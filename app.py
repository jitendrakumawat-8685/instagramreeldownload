import streamlit as st
import instaloader
import os
from PIL import Image
from io import BytesIO
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

# === State Init ===
if 'selected_feature' not in st.session_state:
    st.session_state['selected_feature'] = None

# === Cards ===
st.markdown("### Choose a Feature:")
features = {
    "📸 Post/Reel Downloader": "post",
    "🖼️ Profile Picture Downloader": "dp",
    # "👻 Story Downloader": "story",
    # "📤 Upload to Instagram": "upload",
    "🔍 Profile Viewer": "profile",
    "📁 Download History": "history"
    # "🔐 Login / Logout": "login",
    # "👥 Manage Accounts": "accounts"
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
    # st.markdown("✅ Paste **multiple Instagram post/reel URLs** below, one per line.")
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
                    img = Image.open(BytesIO(img_data))
                    st.image(img, caption="Image")
                    
                    img_path = os.path.join(DOWNLOAD_DIR, f"{owner}.jpg")
                    with open(img_path, "wb") as f:
                        f.write(img_data)

                    # st.success(f"✅ Saved to: {img_path}")

                elif post.typename == "GraphVideo":
                    st.info("🎥 This is a video post.")
                    st.video(post.video_url)

                    vid_data = requests.get(post.video_url).content
                    vid_path = os.path.join(DOWNLOAD_DIR, f"{owner}.mp4")
                    with open(vid_path, "wb") as f:
                        f.write(vid_data)

                elif post.typename == "GraphSidecar":
                    st.info("🌀 This is a carousel post with multiple items:")
                    sidecar_nodes = list(post.get_sidecar_nodes())  # ✅ Convert generator to list ONCE

                    for idx, node in enumerate(sidecar_nodes):
                        st.markdown(f"**Slide {idx + 1}:**")
                        if node.is_video:
                            st.video(node.video_url)
                            vid_data = requests.get(node.video_url).content
                            vid_path = os.path.join(DOWNLOAD_DIR, f"{owner}_video_{idx+1}.mp4")
                            with open(vid_path, "wb") as f:
                                f.write(vid_data)
                        else:
                            img_data = requests.get(node.display_url).content
                            img = Image.open(BytesIO(img_data))
                            st.image(img, caption=f"Image {idx + 1}")

                            img_path = os.path.join(DOWNLOAD_DIR, f"{owner}_image_{idx+1}.jpg")
                            with open(img_path, "wb") as f:
                                f.write(img_data)

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
            img = Image.open(BytesIO(requests.get(profile.profile_pic_url).content))
            img.save(f"{DOWNLOAD_DIR}/{username}_dp.jpg")
            st.image(img, caption=f"{username}'s Profile Picture")
            st.success("✅ Saved.")
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
    st.subheader("📁 Download History")
    files = os.listdir(DOWNLOAD_DIR)
    if files:
        for file in sorted(files, reverse=True):
            st.markdown(f"- `{file}`")
    else:
        st.info("Nothing downloaded yet.")

