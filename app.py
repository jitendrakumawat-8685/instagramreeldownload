import datetime
import streamlit as st
import instaloader
import os
from PIL import Image
from io import BytesIO
import io
import requests
from pathlib import Path
import re

# === Setup ===
st.set_page_config(page_title="Instagram Bot Dashboard", layout="wide")
st.title("📸 Instagram Bot Dashboard")

# ===== Setup Paths =====
DOWNLOAD_DIR = str(Path.home() / "Downloads")

# ===== Configure Instaloader to Avoid Extra Files =====
L = instaloader.Instaloader(
    download_comments=False,
    download_video_thumbnails=False,
    save_metadata=False,
    post_metadata_txt_pattern="",
    compress_json=False
)

# === Initialize download log in session state ===
if 'download_log' not in st.session_state:
    st.session_state['download_log'] = []

# === State Init ===
if 'selected_feature' not in st.session_state:
    st.session_state['selected_feature'] = None

# === Cards ===
st.markdown("### Choose a Feature:")
features = {
    "📸 Post/Reel Downloader": "post",
    "🖼️ Profile Picture Downloader": "dp",
    "🔍 Profile Viewer": "profile",
    "📁 Download History": "history"
}

cols = st.columns(2)
for i, (label, key) in enumerate(features.items()):
    if cols[i % 2].button(label):
        st.session_state['selected_feature'] = key

st.markdown("---")
selected = st.session_state['selected_feature']

# ===== Helper Function to "Summarize" Captions =====
def summarize_caption(caption):
    if not caption:
        return "No caption provided."
    
    # Remove mentions, hashtags, emojis, links
    caption = re.sub(r"@[A-Za-z0-9_]+", "", caption)
    caption = re.sub(r"#\S+", "", caption)
    caption = re.sub(r"http\S+", "", caption)
    caption = re.sub(r"[^\x00-\x7F]+", "", caption)
    
    # Limit to 1-2 key lines
    lines = [line.strip() for line in caption.split('\n') if line.strip()]
    summary = '. '.join(lines[:2]) + ('...' if len(lines) > 2 else '')
    return summary.strip()

# === Feature: Post/Reel Downloader ===
if selected == "post":
    st.subheader("📸 Download Instagram Post or Reel")
    url = st.text_input("Paste Post/Reel URL", key="post_urls")

    def summarize_caption(caption):
        if not caption:
            return "No caption provided."
        # Clean caption
        import re
        caption = re.sub(r"@[A-Za-z0-9_]+", "", caption)
        caption = re.sub(r"#\S+", "", caption)
        caption = re.sub(r"http\S+", "", caption)
        caption = re.sub(r"[^\x00-\x7F]+", "", caption)
        lines = [line.strip() for line in caption.split('\n') if line.strip()]
        summary = '. '.join(lines[:2]) + ('...' if len(lines) > 2 else '')
        return summary.strip()

    def extract_shortcode(url):
        parts = url.strip("/").split("/")
        for part in parts:
            if len(part) > 5 and all(c.isalnum() or c in ['-', '_'] for c in part):
                return part
        return None

    def display_post(post):
        owner = post.owner_username
        st.write(f"👤 **Username**: {owner}")

        summary = summarize_caption(post.caption)
        st.markdown(f"🧠 **Caption Summary:** {summary}")

        if post.typename == "GraphImage":
            st.info("🖼️ This is a single image post.")
            img_data = requests.get(post.url).content
            img = Image.open(io.BytesIO(img_data))
            st.image(img, caption="Image")
            st.download_button(
                label="Download Image",
                data=img_data,
                file_name=f"{owner}.jpg",
                mime="image/jpeg"
            )

        elif post.typename == "GraphVideo":
            st.info("🎥 This is a video post.")
            st.video(post.video_url)
            vid_data = requests.get(post.video_url).content
            st.download_button(
                label="Download Video",
                data=vid_data,
                file_name=f"{owner}.mp4",
                mime="video/mp4"
            )

        elif post.typename == "GraphSidecar":
            st.info("🌀 This is a carousel post with multiple items:")
            for idx, node in enumerate(post.get_sidecar_nodes()):
                st.markdown(f"**Slide {idx + 1}:**")
                if node.is_video:
                    st.video(node.video_url)
                    vid_data = requests.get(node.video_url).content
                    st.download_button(
                        label=f"Download Video {idx + 1}",
                        data=vid_data,
                        file_name=f"{owner}_video_{idx+1}.mp4",
                        mime="video/mp4"
                    )
                else:
                    img_data = requests.get(node.display_url).content
                    img = Image.open(io.BytesIO(img_data))
                    st.image(img, caption=f"Image {idx + 1}")
                    st.download_button(
                        label=f"Download Image {idx + 1}",
                        data=img_data,
                        file_name=f"{owner}_image_{idx+1}.jpg",
                        mime="image/jpeg"
                    )

    if st.button("Download Post", key="download_post"):
        if not url:
            st.warning("⚠️ Please paste a valid Instagram Post or Reel URL.")
            st.stop()
        if "instagram.com" not in url:
            st.error("❌ Invalid URL. Please enter a valid Instagram Post or Reel URL.")
            st.stop()

        shortcode = extract_shortcode(url)
        if not shortcode:
            st.error("❌ Couldn't extract shortcode from URL.")
            st.stop()

        L_anonymous = instaloader.Instaloader(
            download_comments=False,
            download_video_thumbnails=False,
            save_metadata=False,
            post_metadata_txt_pattern="",
            compress_json=False
        )

        # Try downloading anonymously first
        try:
            with st.spinner("Attempting to download without login..."):
                post = instaloader.Post.from_shortcode(L_anonymous.context, shortcode)
                display_post(post)
                st.success("✅ Downloaded without login.")
        except instaloader.exceptions.PrivateProfileNotFollowedException:
            # Post is private, need login
            st.info("🔒 This post appears to be private. Please login to continue.")

            with st.form("login_form"):
                username = st.text_input("Instagram Username", key="login_username")
                password = st.text_input("Instagram Password", type="password", key="login_password")
                submitted = st.form_submit_button("Login and Download")

                if submitted:
                    L_logged_in = instaloader.Instaloader(
                        download_comments=False,
                        download_video_thumbnails=False,
                        save_metadata=False,
                        post_metadata_txt_pattern="",
                        compress_json=False
                    )
                    try:
                        with st.spinner("Logging in..."):
                            L_logged_in.login(username, password)
                        with st.spinner("Downloading post..."):
                            post = instaloader.Post.from_shortcode(L_logged_in.context, shortcode)
                            display_post(post)
                            st.success("✅ Downloaded after login.")
                    except Exception as e:
                        st.error(f"❌ Login or download failed: {e}")
        except instaloader.exceptions.LoginRequiredException:
            # Login required (similar case)
            st.info("🔒 Login required to access this post. Please enter your credentials.")

            with st.form("login_form"):
                username = st.text_input("Instagram Username", key="login_username2")
                password = st.text_input("Instagram Password", type="password", key="login_password2")
                submitted = st.form_submit_button("Login and Download")

                if submitted:
                    L_logged_in = instaloader.Instaloader(
                        download_comments=False,
                        download_video_thumbnails=False,
                        save_metadata=False,
                        post_metadata_txt_pattern="",
                        compress_json=False
                    )
                    try:
                        with st.spinner("Logging in..."):
                            L_logged_in.login(username, password)
                        with st.spinner("Downloading post..."):
                            post = instaloader.Post.from_shortcode(L_logged_in.context, shortcode)
                            display_post(post)
                            st.success("✅ Downloaded after login.")
                    except Exception as e:
                        st.error(f"❌ Login or download failed: {e}")
        except Exception as e:
            st.error(f"❌ Error while downloading post: {e}")
            st.stop()

# === Feature: DP Downloader ===
elif selected == "dp":
    st.subheader("🖼️ Download Profile Picture")
    username = st.text_input("Instagram Username", key="dp_username")
    if st.button("Download DP", key="download_dp"):
        try:
            profile = instaloader.Profile.from_username(L.context, username)
            img_data = requests.get(profile.profile_pic_url).content
            img = Image.open(BytesIO(img_data))
            st.image(img, caption=f"{username}'s Profile Picture")
            st.download_button(
                label="Download Profile Picture",
                data=img_data,
                file_name=f"{username}_dp.jpg",
                mime="image/jpeg"
            )
            # Log download
            st.session_state['download_log'].append({
                "filename": f"{username}_dp.jpg",
                "timestamp": datetime.datetime.now()
            })
            st.success("✅ Ready to download.")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# === Feature: Profile Viewer ===
elif selected == "profile":
    st.subheader("🔍 View Profile")
    username = st.text_input("Enter Username", key="profile_user")
    if st.button("View Profile", key="view_profile"):
        try:
            profile = instaloader.Profile.from_username(L.context, username)
            st.image(profile.profile_pic_url, width=100)
            st.markdown(f"**Name:** {profile.full_name}")
            st.markdown(f"**Username:** `{profile.username}`")
            st.markdown(f"**Followers:** {profile.followers}")
            st.markdown(f"**Following:** {profile.followees}")
            st.markdown(f"**Posts:** {profile.mediacount}")
            st.markdown(f"**Private:** {'Yes 🔒' if profile.is_private else 'No 🔓'}")
            st.markdown(f"**Bio:** {profile.biography}")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# === Feature: Download History ===
elif selected == "history":
    st.subheader("📁 Download History (Session)")

    if st.session_state['download_log']:
        # Show logs sorted by timestamp descending
        sorted_logs = sorted(st.session_state['download_log'], key=lambda x: x['timestamp'], reverse=True)
        for entry in sorted_logs:
            ts_str = entry['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
            st.markdown(f"- `{entry['filename']}` downloaded at {ts_str}")
    else:
        st.info("No downloads in this session yet.")
