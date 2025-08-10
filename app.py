import datetime
import streamlit as st
import os
import re
import requests
from pathlib import Path
from PIL import Image
from io import BytesIO
import instaloader

# =====================
# STREAMLIT PAGE CONFIG
# =====================
st.set_page_config(page_title="Instagram Bot Dashboard", layout="wide")
st.title("📸 Instagram Bot Dashboard")

# =====================
# DOWNLOAD DIRECTORY
# =====================
DOWNLOAD_DIR = str(Path.home() / "Downloads")

# =====================
# INSTALOADER SETTINGS
# =====================
try:
    L = instaloader.Instaloader(
        download_comments=False,
        download_video_thumbnails=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
        compress_json=False
    )
except Exception as e:
    st.error(f"⚠️ Instaloader initialization failed: {e}")
    st.stop()

# =====================
# SESSION STATE INIT
# =====================
if 'download_log' not in st.session_state:
    st.session_state['download_log'] = []

if 'selected_feature' not in st.session_state:
    st.session_state['selected_feature'] = None

# =====================
# FEATURE SELECTION
# =====================
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

# =====================
# HELPER FUNCTIONS
# =====================
def summarize_caption(caption):
    """Clean and shorten the caption text."""
    if not caption:
        return "No caption provided."
    try:
        caption = re.sub(r"@[A-Za-z0-9_]+", "", caption)
        caption = re.sub(r"#\S+", "", caption)
        caption = re.sub(r"http\S+", "", caption)
        caption = re.sub(r"[^\x00-\x7F]+", "", caption)
        lines = [line.strip() for line in caption.split('\n') if line.strip()]
        summary = '. '.join(lines[:2]) + ('...' if len(lines) > 2 else '')
        return summary.strip()
    except Exception:
        return "Caption unavailable."

def safe_request(url):
    """Download content with error handling."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.content
    except Exception:
        return None

# =====================
# FEATURE: POST/REEL DOWNLOADER
# =====================
if selected == "post":
    st.subheader("📸 Download Instagram Post or Reel")
    url = st.text_input("Paste Post/Reel URL", key="post_urls")

    if st.button("Download Post", key="download_post"):
        if not url or "instagram.com" not in url:
            st.warning("⚠️ Please paste a valid Instagram Post/Reel URL.")
            st.stop()

        try:
            with st.spinner("Processing... Please wait..."):
                shortcode = url.strip().split("/")[-2]
                post = instaloader.Post.from_shortcode(L.context, shortcode)

                st.write(f"👤 **Username**: {post.owner_username}")
                summary = summarize_caption(post.caption)
                st.markdown(f"🧠 **Caption Summary:** {summary}")

                # Single Image
                if post.typename == "GraphImage":
                    img_data = safe_request(post.url)
                    if img_data:
                        st.image(Image.open(BytesIO(img_data)), caption="Image")
                        st.download_button("Download Image", img_data, f"{post.owner_username}.jpg", "image/jpeg")
                    else:
                        st.error("❌ Could not fetch the image.")

                # Single Video
                elif post.typename == "GraphVideo":
                    vid_data = safe_request(post.video_url)
                    if vid_data:
                        st.video(post.video_url)
                        st.download_button("Download Video", vid_data, f"{post.owner_username}.mp4", "video/mp4")
                    else:
                        st.error("❌ Could not fetch the video.")

                # Carousel (Multiple Images/Videos)
                elif post.typename == "GraphSidecar":
                    for idx, node in enumerate(post.get_sidecar_nodes()):
                        st.markdown(f"**Slide {idx + 1}:**")
                        if node.is_video:
                            vid_data = safe_request(node.video_url)
                            if vid_data:
                                st.video(node.video_url)
                                st.download_button(f"Download Video {idx+1}", vid_data,
                                                   f"{post.owner_username}_video_{idx+1}.mp4", "video/mp4")
                        else:
                            img_data = safe_request(node.display_url)
                            if img_data:
                                st.image(Image.open(BytesIO(img_data)), caption=f"Image {idx + 1}")
                                st.download_button(f"Download Image {idx+1}", img_data,
                                                   f"{post.owner_username}_image_{idx+1}.jpg", "image/jpeg")

                # Log
                st.session_state['download_log'].append({
                    "filename": f"{post.owner_username}_{post.typename}",
                    "timestamp": datetime.datetime.now()
                })
                st.success("✅ Download complete.")
        except Exception as e:
            st.error(f"❌ Error while downloading: {e}")

# =====================
# FEATURE: DP DOWNLOADER
# =====================
elif selected == "dp":
    st.subheader("🖼️ Download Profile Picture")
    username = st.text_input("Instagram Username", key="dp_username")

    if st.button("Download DP", key="download_dp"):
        if not username:
            st.warning("⚠️ Please enter a username.")
            st.stop()

        try:
            profile = instaloader.Profile.from_username(L.context, username)
            img_data = safe_request(profile.profile_pic_url)
            if img_data:
                st.image(Image.open(BytesIO(img_data)), caption=f"{username}'s Profile Picture")
                st.download_button("Download Profile Picture", img_data, f"{username}_dp.jpg", "image/jpeg")
                st.session_state['download_log'].append({
                    "filename": f"{username}_dp.jpg",
                    "timestamp": datetime.datetime.now()
                })
                st.success("✅ Ready to download.")
            else:
                st.error("❌ Could not fetch profile picture.")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# =====================
# FEATURE: PROFILE VIEWER
# =====================
elif selected == "profile":
    st.subheader("🔍 View Profile")
    username = st.text_input("Enter Username", key="profile_user")

    if st.button("View Profile", key="view_profile"):
        if not username:
            st.warning("⚠️ Please enter a username.")
            st.stop()

        try:
            profile = instaloader.Profile.from_username(L.context, username)
            st.image(profile.profile_pic_url, width=100)
            st.markdown(f"**Name:** {profile.full_name}")
            st.markdown(f"**Username:** `{profile.username}`")
            st.markdown(f"**Followers:** {profile.followers}")
            st.markdown(f"**Following:** {profile.followees}")
            st.markdown(f"**Posts:** {profile.mediacount}")
            st.markdown(f"**Private:** {'Yes 🔒' if profile.is_private else 'No 🔓'}")
            st.markdown(f"**Bio:** {profile.biography or 'No bio available'}")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# =====================
# FEATURE: DOWNLOAD HISTORY
# =====================
elif selected == "history":
    st.subheader("📁 Download History (Session)")

    if st.session_state['download_log']:
        sorted_logs = sorted(st.session_state['download_log'], key=lambda x: x['timestamp'], reverse=True)
        for entry in sorted_logs:
            ts_str = entry['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
            st.markdown(f"- `{entry['filename']}` downloaded at {ts_str}")
    else:
        st.info("No downloads in this session yet.")
