import streamlit as st
import requests
import os
import re
import tempfile
import time
from urllib.parse import urlparse, unquote
import json
import base64
from PIL import Image
import io

# Configure Streamlit page
st.set_page_config(
    page_title="Instagram Video Downloader",
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
    .instagram-gradient {
        background: linear-gradient(45deg, #E1306C, #C13584, #FD1D1D, #F56040, #F77737, #FCAF45, #FFDC80);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .download-btn {
        background: linear-gradient(45deg, #E1306C, #C13584) !important;
        color: white !important;
        border: none !important;
        padding: 10px 20px !important;
        border-radius: 10px !important;
        font-size: 16px !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

# ===== Instagram Downloader Class =====
class InstagramDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.setup_headers()
        
    def setup_headers(self):
        """Setup realistic headers to avoid detection"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        self.session.headers.update(self.headers)
    
    def extract_video_url(self, html_content):
        """Extract video URL from Instagram HTML using multiple methods"""
        video_urls = []
        
        # Method 1: Look for video_url in JSON data
        json_patterns = [
            r'"video_url":"([^"]+)"',
            r'"contentUrl":"([^"]+)"',
            r'"video_url":"([^"]+)"',
            r'src="([^"]+\.mp4[^"]*)"',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                video_url = match.replace('\\u0025', '%').replace('\\u0026', '&')
                if '.mp4' in video_url and video_url not in video_urls:
                    video_urls.append(video_url)
        
        # Method 2: Look for video sources
        video_sources = re.findall(r'src="(https://[^"]+\.mp4\?[^"]+)"', html_content)
        video_urls.extend(video_sources)
        
        # Method 3: Look for additional video URLs
        additional_urls = re.findall(r'https://[^"]+\.mp4[^"]*', html_content)
        video_urls.extend(additional_urls)
        
        # Method 4: Look for Instagram specific video patterns
        insta_patterns = [
            r'{"video":{"url":"([^"]+)"',
            r'video_url":"([^"]+)"',
        ]
        
        for pattern in insta_patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                video_url = match.replace('\\u0025', '%').replace('\\u0026', '&')
                if '.mp4' in video_url and video_url not in video_urls:
                    video_urls.append(video_url)
        
        # Remove duplicates and filter valid URLs
        unique_urls = []
        for url in video_urls:
            if url not in unique_urls and 'instagram.com' not in url:
                unique_urls.append(url)
        
        return unique_urls
    
    def get_video_info(self, url):
        """Get video information including thumbnail"""
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                return None
            
            html_content = response.text
            
            # Extract title/description
            title_match = re.search(r'<title>([^<]+)</title>', html_content)
            title = title_match.group(1) if title_match else "Instagram Video"
            
            # Extract thumbnail
            thumbnail_url = None
            thumbnail_patterns = [
                r'"thumbnail_url":"([^"]+)"',
                r'"og:image" content="([^"]+)"',
                r'property="og:image" content="([^"]+)"',
            ]
            
            for pattern in thumbnail_patterns:
                match = re.search(pattern, html_content)
                if match:
                    thumbnail_url = match.group(1).replace('\\u0026', '&')
                    break
            
            return {
                'title': title.replace('• Instagram', '').strip(),
                'thumbnail': thumbnail_url,
                'url': url
            }
            
        except Exception as e:
            st.error(f"Error getting video info: {str(e)}")
            return None
    
    def download_video(self, url):
        """Download Instagram video using multiple methods"""
        temp_dir = tempfile.gettempdir()
        timestamp = int(time.time())
        
        try:
            # First, try to get the HTML content
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                st.error(f"Failed to access Instagram: Status {response.status_code}")
                return None
            
            html_content = response.text
            
            # Extract video URLs
            video_urls = self.extract_video_url(html_content)
            
            if not video_urls:
                st.error("No video URL found in the page")
                return None
            
            st.info(f"Found {len(video_urls)} potential video sources. Trying each one...")
            
            # Try each video URL
            for i, video_url in enumerate(video_urls, 1):
                try:
                    st.write(f"🔄 Trying source {i}/{len(video_urls)}...")
                    
                    # Download the video
                    video_response = self.session.get(video_url, stream=True, timeout=60)
                    
                    if video_response.status_code == 200:
                        file_path = os.path.join(temp_dir, f'instagram_video_{timestamp}.mp4')
                        
                        # Get file size
                        total_size = int(video_response.headers.get('content-length', 0))
                        
                        # Download with progress
                        downloaded = 0
                        with open(file_path, 'wb') as f:
                            for chunk in video_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                        
                        # Verify download
                        if os.path.exists(file_path) and os.path.getsize(file_path) > 1024:
                            with open(file_path, 'rb') as f:
                                video_data = f.read()
                            
                            # Clean up
                            os.remove(file_path)
                            
                            st.success(f"✅ Successfully downloaded from source {i}!")
                            return video_data
                        else:
                            st.warning(f"Source {i} download incomplete, trying next...")
                    
                except Exception as e:
                    st.warning(f"Source {i} failed: {str(e)}")
                    continue
            
            # If all methods fail, try alternative approach
            return self.try_alternative_methods(url, html_content)
            
        except Exception as e:
            st.error(f"Download failed: {str(e)}")
            return None
    
    def try_alternative_methods(self, url, html_content):
        """Try alternative methods to download the video"""
        st.info("🔄 Trying advanced extraction methods...")
        
        try:
            # Method: Look for JSON data containing video info
            json_pattern = r'window\._sharedData\s*=\s*({.+?})\s*;\s*</script>'
            match = re.search(json_pattern, html_content)
            
            if match:
                json_data = match.group(1)
                data = json.loads(json_data)
                
                # Navigate through JSON to find video URL
                def find_video_url(obj, path=[]):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if isinstance(value, str) and value.startswith('http') and '.mp4' in value:
                                return value
                            result = find_video_url(value, path + [key])
                            if result:
                                return result
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            result = find_video_url(item, path + [i])
                            if result:
                                return result
                    return None
                
                video_url = find_video_url(data)
                if video_url:
                    st.info("Found video URL in JSON data")
                    video_response = self.session.get(video_url, stream=True, timeout=60)
                    
                    if video_response.status_code == 200:
                        temp_dir = tempfile.gettempdir()
                        timestamp = int(time.time())
                        file_path = os.path.join(temp_dir, f'instagram_alt_{timestamp}.mp4')
                        
                        with open(file_path, 'wb') as f:
                            for chunk in video_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        with open(file_path, 'rb') as f:
                            video_data = f.read()
                        
                        os.remove(file_path)
                        return video_data
            
            return None
            
        except Exception as e:
            st.warning(f"Alternative method failed: {str(e)}")
            return None

# ===== Streamlit UI =====
def main():
    st.markdown("""
    <div class="instagram-gradient">
        <h1>📥 Instagram Video Downloader</h1>
        <p>Download Instagram videos without limits • High quality • Fast</p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize downloader
    if 'downloader' not in st.session_state:
        st.session_state.downloader = InstagramDownloader()
    
    if 'video_data' not in st.session_state:
        st.session_state.video_data = None
    if 'video_info' not in st.session_state:
        st.session_state.video_info = None

    # Sidebar
    with st.sidebar:
        st.header("🎯 Features")
        st.success("""
        ✅ No Rate Limits
        ✅ High Quality Videos
        ✅ Fast Download
        ✅ No Watermarks
        ✅ All Instagram Formats:
           - Reels
           - Posts
           - Stories
           - IGTV
        """)
        
        st.markdown("---")
        st.header("📋 How To Use")
        st.info("""
        1. Copy Instagram video URL
        2. Paste in the input below
        3. Click 'Get Video Info'
        4. Click 'Download Video'
        5. Save to your device
        """)
        
        st.markdown("---")
        if st.button("🔄 Clear All", use_container_width=True):
            st.session_state.video_data = None
            st.session_state.video_info = None
            st.rerun()

    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🔗 Paste Instagram URL")
        url = st.text_input(
            "Instagram Video URL:",
            placeholder="https://www.instagram.com/reel/... or https://www.instagram.com/p/...",
            label_visibility="collapsed"
        )
        
        if url:
            if not url.startswith('https://www.instagram.com/'):
                st.error("❌ Please enter a valid Instagram URL")
            else:
                st.success("✅ Valid Instagram URL detected!")

    with col2:
        st.markdown("### ⚡ Quick Actions")
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("🔍 Get Video Info", use_container_width=True):
                if url and url.startswith('https://www.instagram.com/'):
                    with st.spinner("Fetching video information..."):
                        info = st.session_state.downloader.get_video_info(url)
                        if info:
                            st.session_state.video_info = info
                            st.success("✅ Video info retrieved!")
                        else:
                            st.error("❌ Could not fetch video info")
                else:
                    st.error("Please enter a valid Instagram URL first")

        with col_b:
            if st.button("💾 Download Video", use_container_width=True):
                if url and url.startswith('https://www.instagram.com/'):
                    with st.spinner("Downloading video... This may take a moment..."):
                        video_data = st.session_state.downloader.download_video(url)
                        if video_data:
                            st.session_state.video_data = video_data
                            file_size_mb = len(video_data) / (1024 * 1024)
                            st.success(f"✅ Download complete! Size: {file_size_mb:.1f} MB")
                        else:
                            st.error("❌ Download failed. Please try again or check the URL")
                else:
                    st.error("Please enter a valid Instagram URL first")

    # Display video information
    if st.session_state.video_info:
        info = st.session_state.video_info
        st.markdown("---")
        st.markdown("### 📊 Video Information")
        
        col_info, col_thumb = st.columns([2, 1])
        
        with col_info:
            st.write(f"**Title:** {info['title']}")
            st.write(f"**Source:** {info['url']}")
            st.write("**Status:** ✅ Ready for download")
            
        with col_thumb:
            if info['thumbnail']:
                try:
                    response = requests.get(info['thumbnail'], timeout=10)
                    img = Image.open(io.BytesIO(response.content))
                    st.image(img, caption="Video Thumbnail", use_container_width=True)
                except:
                    st.info("🎬 Video thumbnail available")

    # Download section
    if st.session_state.video_data:
        st.markdown("---")
        st.markdown("### 💾 Save Video")
        
        info = st.session_state.video_info or {}
        title = info.get('title', 'instagram_video')
        
        # Create safe filename
        safe_title = re.sub(r'[^\w\s-]', '', title)
        safe_title = re.sub(r'[-\s]+', '_', safe_title).strip('_')
        filename = f"{safe_title}.mp4"
        
        st.download_button(
            label="⬇️ Download Video File",
            data=st.session_state.video_data,
            file_name=filename,
            mime="video/mp4",
            use_container_width=True,
            key="download_btn"
        )
        
        # Video preview
        st.markdown("### 👀 Video Preview")
        video_base64 = base64.b64encode(st.session_state.video_data).decode()
        video_html = f'''
        <video width="100%" controls>
            <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
        '''
        st.markdown(video_html, unsafe_allow_html=True)

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "For personal use only • Respect Instagram's Terms of Service"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()