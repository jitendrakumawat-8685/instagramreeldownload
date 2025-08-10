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
    if st.button("Download Post", key="download_post"):
        try:
            if not url:
                st.warning("⚠️ Please paste a valid Instagram Post or Reel URL.")
                st.stop()
            if "instagram.com" not in url:
                st.error("❌ Invalid URL. Please enter a valid Instagram Post or Reel URL.")
                st.stop()
            with st.spinner("Processing... Please wait..."): 
                shortcode = url.strip().split("/")[-2]
                post = instaloader.Post.from_shortcode(L.context, shortcode)
                progress = st.progress(0)

                L.download_post(post, target=post.owner_username)
                owner = post.owner_username
                st.write(f"👤 **Username**: {owner}")

                summary = summarize_caption(post.caption)
                st.markdown(f"🧠 **Caption Summary:** {summary}")

                # Check post type
                if post.typename == "GraphImage":
                    st.info("🖼️ This is a single image post.")
                    img_data = requests.get(post.url).content
                    img = Image.open(io.BytesIO(img_data))
                    st.image(img, caption="Image")
                    
                    st.download_button(
                        label="Download Image",
                        data=img_data,
                        file_name=f"{post.owner_username}.jpg",
                        mime="image/jpeg"
                    )
                    # Log download
                    # st.session_state['download_log'].append({
                    #     "filename": f"{post.owner_username}.jpg",
                    #     "timestamp": datetime.datetime.now()
                    # })

                elif post.typename == "GraphVideo":
                    st.info("🎥 This is a video post.")
                    st.video(post.video_url)

                    vid_data = requests.get(post.video_url).content
                    st.download_button(
                        label="Download Video",
                        data=vid_data,
                        file_name=f"{post.owner_username}.mp4",
                        mime="video/mp4"
                    )
                    # Log download
                    # st.session_state['download_log'].append({
                    #     "filename": f"{post.owner_username}.mp4",
                    #     "timestamp": datetime.datetime.now()
                    # })

                elif post.typename == "GraphSidecar":
                    st.info("🌀 This is a carousel post with multiple items:")
                    sidecar_nodes = list(post.get_sidecar_nodes())

                    for idx, node in enumerate(sidecar_nodes):
                        st.markdown(f"**Slide {idx + 1}:**")
                        if node.is_video:
                            st.video(node.video_url)
                            vid_data = requests.get(node.video_url).content
                            st.download_button(
                                label=f"Download Video {idx + 1}",
                                data=vid_data,
                                file_name=f"{post.owner_username}_video_{idx+1}.mp4",
                                mime="video/mp4"
                            )
                            # Log download
                            # st.session_state['download_log'].append({
                            #     "filename": f"{post.owner_username}_video_{idx+1}.mp4",
                            #     "timestamp": datetime.datetime.now()
                            # })
                        else:
                            img_data = requests.get(node.display_url).content
                            img = Image.open(io.BytesIO(img_data))
                            st.image(img, caption=f"Image {idx + 1}")
                            st.download_button(
                                label=f"Download Image {idx + 1}",
                                data=img_data,
                                file_name=f"{post.owner_username}_image_{idx+1}.jpg",
                                mime="image/jpeg"
                            )
                            # Log download
                            # st.session_state['download_log'].append({
                            #     "filename": f"{post.owner_username}_image_{idx+1}.jpg",
                            #     "timestamp": datetime.datetime.now()
                            # })

                progress.progress(100)
                st.success("✅ Download complete.")
        except Exception as e:
            st.error(f"❌ Error: {e}")

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
            # st.image(profile.profile_pic_url, width=100)
            img_response = requests.get(profile.profile_pic_url)
            img = Image.open(BytesIO(img_response.content))
            st.image(img, width=150)
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
