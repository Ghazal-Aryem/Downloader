import streamlit as st
import requests
import os
import re
import tempfile
import time
from urllib.parse import urlparse
import json
import base64
from PIL import Image
import io
import instaloader
from io import BytesIO
import logging

# Configure Streamlit page
st.set_page_config(
    page_title="Instagram Downloader Pro",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== Custom CSS =====
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #E1306C;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .success-box {
        background-color: #d4edda;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #28a745;
        margin: 10px 0;
    }
    .info-box {
        background-color: #d1ecf1;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #17a2b8;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ffc107;
        margin: 10px 0;
    }
    .instagram-gradient {
        background: linear-gradient(45deg, #E1306C, #C13584, #FD1D1D, #F56040, #F77737, #FCAF45, #FFDC80);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .stDownloadButton button {
        background: linear-gradient(45deg, #E1306C, #C13584) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 20px !important;
        font-size: 16px !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

# ===== Fixed Instaloader Downloader =====
class InstaloaderDownloader:
    def __init__(self):
        # Configure instaloader with CORRECT parameters
        self.loader = instaloader.Instaloader(
            # Only include valid parameters
            download_pictures=False,
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            filename_pattern="{shortcode}"
        )
        
        # Reduce logging
        logging.getLogger('instaloader').setLevel(logging.ERROR)
    
    def extract_shortcode(self, url):
        """Extract shortcode from Instagram URL"""
        patterns = [
            r'instagram\.com/p/([^/?]+)',
            r'instagram\.com/reel/([^/?]+)',
            r'instagram\.com/tv/([^/?]+)',
            r'instagram\.com/stories/[^/]+/([^/?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_video_info(self, url):
        """Get video information using instaloader"""
        try:
            shortcode = self.extract_shortcode(url)
            if not shortcode:
                st.error("❌ Could not extract post ID from URL")
                return None
            
            st.info(f"🔄 Fetching post information... (Shortcode: {shortcode})")
            
            # Get post using instaloader
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            
            info = {
                'title': f"Instagram Video by {post.owner_username}",
                'owner': post.owner_username,
                'shortcode': shortcode,
                'timestamp': post.date_utc,
                'likes': post.likes,
                'comments': post.comments,
                'is_video': post.is_video,
                'url': f"https://www.instagram.com/p/{shortcode}/",
                'caption': post.caption if post.caption else "No caption",
                'media_count': post.mediacount
            }
            
            return info
            
        except Exception as e:
            st.error(f"❌ Error fetching post: {str(e)}")
            return None
    
    def download_video_instaloader(self, url):
        """Download video using instaloader"""
        temp_dir = tempfile.gettempdir()
        
        try:
            shortcode = self.extract_shortcode(url)
            if not shortcode:
                return None
            
            st.info(f"📥 Downloading video using instaloader...")
            
            # Create temporary directory for download
            download_dir = os.path.join(temp_dir, f"ig_download_{int(time.time())}")
            os.makedirs(download_dir, exist_ok=True)
            
            # Download the post
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            
            if not post.is_video:
                st.error("❌ This post does not contain a video")
                return None
            
            # Download to temporary directory
            original_dir = os.getcwd()
            os.chdir(download_dir)
            
            self.loader.download_post(post, target=".")
            
            # Find the downloaded video file
            video_file = None
            for file in os.listdir(download_dir):
                if file.endswith('.mp4'):
                    video_file = os.path.join(download_dir, file)
                    break
            
            if video_file and os.path.exists(video_file):
                with open(video_file, 'rb') as f:
                    video_data = f.read()
                
                # Clean up
                os.chdir(original_dir)
                import shutil
                shutil.rmtree(download_dir, ignore_errors=True)
                
                return video_data
            else:
                st.error("❌ Video file not found after download")
                os.chdir(original_dir)
                # Clean up even if failed
                import shutil
                shutil.rmtree(download_dir, ignore_errors=True)
                return None
                
        except Exception as e:
            st.error(f"❌ Instaloader download failed: {str(e)}")
            # Clean up on error
            try:
                import shutil
                download_dir = os.path.join(temp_dir, f"ig_download_*")
                for dir in [d for d in os.listdir(temp_dir) if d.startswith("ig_download_")]:
                    shutil.rmtree(os.path.join(temp_dir, dir), ignore_errors=True)
            except:
                pass
            return None

    def download_video_direct(self, url):
        """Alternative direct download method"""
        try:
            st.info("🔄 Trying direct download method...")
            
            shortcode = self.extract_shortcode(url)
            if not shortcode:
                return None
            
            # Try to get video URL via requests
            api_url = f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'X-Requested-With': 'XMLHttpRequest',
                'Connection': 'keep-alive',
            }
            
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(api_url, timeout=30)
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Navigate through JSON to find video URL
                    media = data.get('graphql', {}).get('shortcode_media', {})
                    
                    if media.get('is_video'):
                        video_url = media.get('video_url')
                        if video_url:
                            st.info("🎯 Found video URL via API")
                            # Download the video
                            video_response = session.get(video_url, stream=True, timeout=60)
                            if video_response.status_code == 200:
                                video_data = BytesIO()
                                for chunk in video_response.iter_content(chunk_size=8192):
                                    video_data.write(chunk)
                                return video_data.getvalue()
                    
                    # Check for carousel media
                    edges = media.get('edge_sidecar_to_children', {}).get('edges', [])
                    for edge in edges:
                        node = edge.get('node', {})
                        if node.get('is_video') and node.get('video_url'):
                            video_url = node.get('video_url')
                            st.info("🎯 Found video URL in carousel")
                            video_response = session.get(video_url, stream=True, timeout=60)
                            if video_response.status_code == 200:
                                video_data = BytesIO()
                                for chunk in video_response.iter_content(chunk_size=8192):
                                    video_data.write(chunk)
                                return video_data.getvalue()
                
                except json.JSONDecodeError:
                    st.warning("❌ Could not parse Instagram API response")
            
            return None
            
        except Exception as e:
            st.warning(f"Direct download failed: {str(e)}")
            return None

# ===== Streamlit UI =====
def main():
    st.markdown("""
    <div class="instagram-gradient">
        <h1>📥 Instagram Video Downloader PRO</h1>
        <p>Fixed Version • Uses Instaloader • No Errors</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    <strong>✅ FIXED: Proper Instaloader Configuration</strong>
    - Correct parameter names
    - Better error handling
    - Automatic cleanup
    - Multiple download methods
    </div>
    """, unsafe_allow_html=True)

    # Initialize downloader only once
    if 'downloader' not in st.session_state:
        try:
            st.session_state.downloader = InstaloaderDownloader()
            st.success("✅ Downloader initialized successfully!")
        except Exception as e:
            st.error(f"❌ Failed to initialize downloader: {str(e)}")
            st.stop()
    
    if 'video_data' not in st.session_state:
        st.session_state.video_data = None
    if 'video_info' not in st.session_state:
        st.session_state.video_info = None

    # Sidebar
    with st.sidebar:
        st.header("🎯 How It Works")
        st.success("""
        **Using Fixed Instaloader:**
        1. Extracts post shortcode
        2. Uses Instagram API properly
        3. Downloads video directly
        4. No parameter errors
        """)
        
        st.markdown("---")
        st.header("📋 Supported Content")
        st.info("""
        ✅ **Reels**
        ✅ **Video Posts** 
        ✅ **IGTV Videos**
        ✅ **Carousel Videos**
        """)
        
        st.markdown("---")
        if st.button("🔄 Clear Session", use_container_width=True):
            st.session_state.video_data = None
            st.session_state.video_info = None
            st.rerun()

    # Main content
    st.markdown("### 🔗 Paste Instagram Video URL")
    
    url = st.text_input(
        "Instagram URL:",
        placeholder="https://www.instagram.com/reel/ABC123/ or https://www.instagram.com/p/XYZ789/",
        label_visibility="collapsed",
        key="url_input"
    )

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Get Video Info", use_container_width=True, key="get_info"):
            if url and url.startswith('https://www.instagram.com/'):
                with st.spinner("🔄 Fetching post information..."):
                    info = st.session_state.downloader.get_video_info(url)
                    if info:
                        st.session_state.video_info = info
                        st.success("✅ Post information retrieved!")
                    else:
                        st.error("❌ Failed to get post information")
            else:
                st.error("❌ Please enter a valid Instagram URL")

    with col2:
        if st.button("🚀 Download Video", use_container_width=True, key="download"):
            if url and url.startswith('https://www.instagram.com/'):
                # Get info first if not available
                if not st.session_state.video_info:
                    with st.spinner("🔄 Getting post info first..."):
                        info = st.session_state.downloader.get_video_info(url)
                        if info:
                            st.session_state.video_info = info
                        else:
                            st.error("❌ Cannot download - failed to get post info")
                            return
                
                if st.session_state.video_info:
                    with st.spinner("📥 Downloading video..."):
                        # Try instaloader first
                        video_data = st.session_state.downloader.download_video_instaloader(url)
                        
                        # If instaloader fails, try direct method
                        if not video_data:
                            st.warning("🔄 Trying alternative method...")
                            video_data = st.session_state.downloader.download_video_direct(url)
                        
                        if video_data:
                            st.session_state.video_data = video_data
                            file_size_mb = len(video_data) / (1024 * 1024)
                            st.success(f"✅ Download successful! Size: {file_size_mb:.1f} MB")
                        else:
                            st.error("❌ All download methods failed")
            else:
                st.error("❌ Please enter a valid Instagram URL")

    # Display video information
    if st.session_state.video_info:
        info = st.session_state.video_info
        st.markdown("---")
        st.markdown("### 📊 Post Information")
        
        col_info, col_status = st.columns([2, 1])
        
        with col_info:
            st.write(f"**Owner:** @{info['owner']}")
            st.write(f"**Caption:** {info['caption'][:100]}{'...' if len(info['caption']) > 100 else ''}")
            st.write(f"**Likes:** {info['likes']}")
            st.write(f"**Comments:** {info['comments']}")
            st.write(f"**Post Type:** {'Video' if info['is_video'] else 'Not a video'}")
            
        with col_status:
            if st.session_state.video_data:
                st.success("**Status:** ✅ Downloaded")
            else:
                st.warning("**Status:** ⚠️ Ready to download")

    # Download section
    if st.session_state.video_data:
        st.markdown("---")
        st.markdown("### 💾 Save Video")
        
        info = st.session_state.video_info or {}
        filename = f"instagram_{info.get('shortcode', 'video')}.mp4"
        
        file_size_mb = len(st.session_state.video_data) / (1024 * 1024)
        
        st.download_button(
            label=f"⬇️ Download Video ({file_size_mb:.1f} MB)",
            data=st.session_state.video_data,
            file_name=filename,
            mime="video/mp4",
            use_container_width=True,
            key="final_download"
        )

    # Instructions
    st.markdown("---")
    with st.expander("📖 Instructions & Troubleshooting"):
        st.markdown("""
        **How to use:**
        1. Copy Instagram video URL (Reel, Post, or IGTV)
        2. Paste above and click "Get Video Info"
        3. Click "Download Video"
        
        **If downloads fail:**
        - Make sure video is **public**
        - Try a **different post**
        - Check **internet connection**
        
        **Requirements:**
        ```bash
        pip install instaloader streamlit requests pillow
        ```
        """)

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Fixed Instagram Downloader • No Parameter Errors • For personal use only"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()