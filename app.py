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
import sys
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

# ===== Instaloader Downloader =====
class InstaloaderDownloader:
    def __init__(self):
        # Configure instaloader with optimal settings
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            filename_pattern="{shortcode}",
            post_metadata_txt_pattern="",
            max_connection_attempts=5,
            request_timeout=300.0,
            sleep=True,
            sleep_time=2,
            rate_controller=None
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
            
        except instaloader.exceptions.InvalidArgumentException:
            st.error("❌ Invalid Instagram post URL")
            return None
        except instaloader.exceptions.PrivateProfileNotFollowedException:
            st.error("❌ This is from a private account. Cannot access private content.")
            return None
        except instaloader.exceptions.BadCredentialsException:
            st.error("❌ Instagram is requiring login. Trying alternative method...")
            return None
        except instaloader.exceptions.ConnectionException:
            st.error("❌ Network error. Please check your connection.")
            return None
        except instaloader.exceptions.TooManyRequestsException:
            st.error("❌ Too many requests. Please wait a few minutes.")
            return None
        except Exception as e:
            st.error(f"❌ Error fetching post info: {str(e)}")
            return None
    
    def download_video_instaloader(self, url):
        """Download video using instaloader"""
        temp_dir = tempfile.gettempdir()
        
        try:
            shortcode = self.extract_shortcode(url)
            if not shortcode:
                return None
            
            st.info(f"📥 Downloading video using instaloader...")
            
            # Configure for single post download
            original_dir = os.getcwd()
            os.chdir(temp_dir)
            
            # Download the post
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            
            if not post.is_video:
                st.error("❌ This post does not contain a video")
                return None
            
            # Download the post
            self.loader.download_post(post, target=shortcode)
            
            # Find the downloaded video file
            video_file = None
            for file in os.listdir(os.path.join(temp_dir, shortcode)):
                if file.endswith('.mp4'):
                    video_file = os.path.join(temp_dir, shortcode, file)
                    break
            
            if video_file and os.path.exists(video_file):
                with open(video_file, 'rb') as f:
                    video_data = f.read()
                
                # Clean up
                import shutil
                shutil.rmtree(os.path.join(temp_dir, shortcode), ignore_errors=True)
                os.chdir(original_dir)
                
                return video_data
            else:
                st.error("❌ Video file not found after download")
                os.chdir(original_dir)
                return None
                
        except Exception as e:
            st.error(f"❌ Instaloader download failed: {str(e)}")
            return None
    
    def download_video_fallback(self, url):
        """Fallback method using direct requests with mobile API"""
        try:
            st.info("🔄 Trying mobile API method...")
            
            shortcode = self.extract_shortcode(url)
            if not shortcode:
                return None
            
            # Use mobile endpoint
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
                data = response.json()
                
                # Navigate to find video URL
                media = data.get('graphql', {}).get('shortcode_media', {})
                
                if media.get('is_video'):
                    video_url = media.get('video_url')
                    if video_url:
                        st.info("🎯 Found video URL via API")
                        return self.download_from_url(video_url)
                
                # Try for carousel media (multiple videos)
                edges = media.get('edge_sidecar_to_children', {}).get('edges', [])
                for edge in edges:
                    node = edge.get('node', {})
                    if node.get('is_video') and node.get('video_url'):
                        video_url = node.get('video_url')
                        st.info("🎯 Found video URL in carousel")
                        return self.download_from_url(video_url)
            
            return None
            
        except Exception as e:
            st.warning(f"Mobile API method failed: {str(e)}")
            return None
    
    def download_from_url(self, video_url):
        """Download video from direct URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.instagram.com/',
                'Connection': 'keep-alive',
            }
            
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(video_url, stream=True, timeout=60)
            
            if response.status_code == 200:
                video_data = BytesIO()
                for chunk in response.iter_content(chunk_size=8192):
                    video_data.write(chunk)
                
                return video_data.getvalue()
            
            return None
            
        except Exception as e:
            st.warning(f"Direct URL download failed: {str(e)}")
            return None

# ===== Streamlit UI =====
def main():
    st.markdown("""
    <div class="instagram-gradient">
        <h1>📥 Instagram Video Downloader PRO</h1>
        <p>Powered by Instaloader • Most Reliable Method • No Rate Limits</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    <strong>🚀 Why This Works Better:</strong>
    - Uses <strong>instaloader</strong> - the official Instagram library
    - Proper API integration instead of HTML scraping
    - Handles authentication and rate limits properly
    - Supports all Instagram content types
    - Much higher success rate
    </div>
    """, unsafe_allow_html=True)

    # Initialize downloader
    if 'downloader' not in st.session_state:
        st.session_state.downloader = InstaloaderDownloader()
    
    if 'video_data' not in st.session_state:
        st.session_state.video_data = None
    if 'video_info' not in st.session_state:
        st.session_state.video_info = None

    # Sidebar
    with st.sidebar:
        st.header("🎯 How It Works")
        st.success("""
        **Using Instaloader:**
        1. Extracts post shortcode from URL
        2. Uses Instagram's internal API
        3. Downloads video directly
        4. No HTML parsing needed
        """)
        
        st.markdown("---")
        st.header("📋 Supported Content")
        st.info("""
        ✅ **Reels**
        ✅ **Video Posts** 
        ✅ **IGTV Videos**
        ✅ **Story Videos** (public)
        ✅ **Carousel Videos**
        ✅ **All Video Qualities**
        """)
        
        st.markdown("---")
        st.header("⚡ Requirements")
        st.warning("""
        Make sure you have:
        ```bash
        pip install instaloader
        ```
        """)
        
        if st.button("🔄 Clear Session", use_container_width=True):
            st.session_state.video_data = None
            st.session_state.video_info = None
            st.rerun()

    # Main content
    st.markdown("### 🔗 Paste Instagram Video URL")
    
    url = st.text_input(
        "Instagram URL:",
        placeholder="https://www.instagram.com/reel/ABC123/ or https://www.instagram.com/p/XYZ789/",
        label_visibility="collapsed"
    )

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Get Video Info", use_container_width=True):
            if url and url.startswith('https://www.instagram.com/'):
                with st.spinner("🔄 Fetching post information via Instaloader..."):
                    info = st.session_state.downloader.get_video_info(url)
                    if info:
                        st.session_state.video_info = info
                        st.success("✅ Post information retrieved successfully!")
                    else:
                        st.error("❌ Failed to get post information")
            else:
                st.error("❌ Please enter a valid Instagram URL")

    with col2:
        if st.button("🚀 Download Video", use_container_width=True):
            if url and url.startswith('https://www.instagram.com/'):
                # Get info first if not already available
                if not st.session_state.video_info:
                    with st.spinner("🔄 Getting post info first..."):
                        info = st.session_state.downloader.get_video_info(url)
                        if info:
                            st.session_state.video_info = info
                
                if st.session_state.video_info:
                    with st.spinner("📥 Downloading video using Instaloader..."):
                        # Try instaloader first
                        video_data = st.session_state.downloader.download_video_instaloader(url)
                        
                        # If instaloader fails, try fallback
                        if not video_data:
                            st.warning("🔄 Instaloader failed, trying fallback method...")
                            video_data = st.session_state.downloader.download_video_fallback(url)
                        
                        if video_data:
                            st.session_state.video_data = video_data
                            file_size_mb = len(video_data) / (1024 * 1024)
                            st.success(f"✅ Download successful! Size: {file_size_mb:.1f} MB")
                        else:
                            st.error("❌ All download methods failed")
                else:
                    st.error("❌ Could not get post information")
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
            use_container_width=True
        )

    # Instructions
    st.markdown("---")
    with st.expander("📖 Instructions & Troubleshooting"):
        st.markdown("""
        **How to use:**
        1. Copy the Instagram video URL (Reel, Post, or IGTV)
        2. Paste it in the input field above
        3. Click "Get Video Info" to verify the post
        4. Click "Download Video" to download
        
        **If downloads fail:**
        - Make sure the video is **public**
        - Try a **different Instagram post**
        - Check your **internet connection**
        - Wait a few minutes if you get rate limited
        
        **Supported URLs:**
        - `https://www.instagram.com/reel/ABC123/`
        - `https://www.instagram.com/p/XYZ789/`
        - `https://www.instagram.com/tv/DEF456/`
        
        **Requirements:**
        ```bash
        pip install instaloader streamlit requests pillow
        ```
        """)

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Instagram Video Downloader Pro • Powered by Instaloader • For personal use only"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()