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
import random

# Configure Streamlit page
st.set_page_config(
    page_title="Instagram Video Downloader Pro",
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
</style>
""", unsafe_allow_html=True)

# ===== Advanced Instagram Downloader =====
class AdvancedInstagramDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.setup_headers()
        
    def setup_headers(self):
        """Setup realistic headers to avoid detection"""
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        ]
        
        self.headers = {
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
        self.rotate_user_agent()
    
    def rotate_user_agent(self):
        """Rotate user agent to avoid detection"""
        self.headers['User-Agent'] = random.choice(self.user_agents)
        self.session.headers.update(self.headers)
    
    def get_video_info(self, url):
        """Get video information"""
        try:
            self.rotate_user_agent()
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                return None
            
            html_content = response.text
            
            # Extract title
            title_match = re.search(r'<title>([^<]+)</title>', html_content)
            title = title_match.group(1) if title_match else "Instagram Video"
            
            return {
                'title': title.replace('• Instagram', '').strip(),
                'url': url,
                'html_content': html_content
            }
            
        except Exception as e:
            st.error(f"Error getting video info: {str(e)}")
            return None
    
    def extract_video_urls_advanced(self, html_content):
        """Advanced video URL extraction using multiple methods"""
        all_video_urls = []
        
        st.info("🔍 Scanning for video sources...")
        
        # Method 1: Extract from JSON-LD structured data
        try:
            json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
            json_ld_matches = re.findall(json_ld_pattern, html_content, re.DOTALL)
            for json_ld in json_ld_matches:
                try:
                    data = json.loads(json_ld)
                    # Navigate through JSON to find video content
                    if isinstance(data, dict):
                        content_url = data.get('contentUrl') or data.get('video', {}).get('contentUrl')
                        if content_url and '.mp4' in content_url:
                            all_video_urls.append(content_url)
                except:
                    pass
        except Exception as e:
            st.warning(f"JSON-LD extraction failed: {e}")
        
        # Method 2: Look for video URLs in script tags
        script_pattern = r'<script[^>]*>(.*?)</script>'
        scripts = re.findall(script_pattern, html_content, re.DOTALL)
        
        for script in scripts:
            # Look for video_url in script content
            video_patterns = [
                r'video_url":"([^"]+)"',
                r'"video_url":"([^"]+)"',
                r'videoUrl":"([^"]+)"',
                r'contentUrl":"([^"]+)"',
                r'src="([^"]+\.mp4[^"]*)"',
                r'video_url\\":\\"([^"]+)\\"',
                r'playable_url":"([^"]+)"',
                r'playable_url_quality_hd":"([^"]+)"',
            ]
            
            for pattern in video_patterns:
                matches = re.findall(pattern, script)
                for match in matches:
                    video_url = (match.replace('\\u0025', '%')
                                .replace('\\u0026', '&')
                                .replace('\\/', '/')
                                .replace('\\\\', ''))
                    if '.mp4' in video_url and 'instagram.com' not in video_url:
                        all_video_urls.append(video_url)
        
        # Method 3: Direct MP4 URL search in entire HTML
        mp4_patterns = [
            r'https://[^"]+\.mp4\?[^"]+',
            r'https://scontent[^"]+\.mp4[^"]*',
            r'https://video[^"]+\.mp4[^"]*',
        ]
        
        for pattern in mp4_patterns:
            matches = re.findall(pattern, html_content)
            all_video_urls.extend(matches)
        
        # Method 4: Look for Instagram's specific data structures
        try:
            # Extract from window._sharedData
            shared_data_pattern = r'window\._sharedData\s*=\s*({.+?})\s*;\s*</script>'
            shared_match = re.search(shared_data_pattern, html_content, re.DOTALL)
            if shared_match:
                shared_data = json.loads(shared_match.group(1))
                video_urls_from_shared = self.extract_from_shared_data(shared_data)
                all_video_urls.extend(video_urls_from_shared)
        except Exception as e:
            st.warning(f"Shared data extraction failed: {e}")
        
        # Method 5: Look for additional data structures
        additional_patterns = [
            r'window\.__additionalDataLoaded[^}]+"video_url":"([^"]+)"',
            r'"video_versions":\[[^]]+"url":"([^"]+)"',
        ]
        
        for pattern in additional_patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                video_url = match.replace('\\u0026', '&').replace('\\/', '/')
                if '.mp4' in video_url:
                    all_video_urls.append(video_url)
        
        # Clean and deduplicate URLs
        clean_urls = []
        for url in all_video_urls:
            # Clean the URL
            clean_url = (url.replace('\\u0026', '&')
                        .replace('\\/', '/')
                        .replace('\\\\', '')
                        .replace('\\u0025', '%'))
            
            # Validate it's a proper URL
            if (clean_url.startswith('http') and 
                '.mp4' in clean_url and 
                'instagram.com' not in clean_url and
                clean_url not in clean_urls):
                clean_urls.append(clean_url)
        
        st.info(f"🎯 Found {len(clean_urls)} potential video sources")
        return clean_urls
    
    def extract_from_shared_data(self, data):
        """Recursively extract video URLs from shared data"""
        video_urls = []
        
        def search_dict(obj):
            if isinstance(obj, dict):
                # Check for video URLs in common Instagram structures
                if (obj.get('__typename') in ['XDTVideo', 'Video'] and 
                    obj.get('video_versions')):
                    for version in obj.get('video_versions', []):
                        if version.get('url'):
                            video_urls.append(version['url'])
                
                # Check for video_url directly
                if obj.get('video_url'):
                    video_urls.append(obj['video_url'])
                
                # Check for display_url that might be video
                if (obj.get('display_url') and 
                    '.mp4' in obj.get('display_url', '')):
                    video_urls.append(obj['display_url'])
                
                # Recursively search
                for value in obj.values():
                    search_dict(value)
                    
            elif isinstance(obj, list):
                for item in obj:
                    search_dict(item)
        
        search_dict(data)
        return video_urls
    
    def download_video(self, url):
        """Download Instagram video using advanced methods"""
        temp_dir = tempfile.gettempdir()
        timestamp = int(time.time())
        
        try:
            # Get HTML content first
            self.rotate_user_agent()
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                st.error(f"❌ Failed to access Instagram (Status: {response.status_code})")
                return None
            
            html_content = response.text
            
            # Extract video URLs using advanced methods
            video_urls = self.extract_video_urls_advanced(html_content)
            
            if not video_urls:
                st.error("❌ No video URLs found. Instagram may have changed their structure.")
                st.info("💡 Try these solutions:")
                st.write("1. Make sure the video is public")
                st.write("2. Try a different Instagram post")
                st.write("3. The video might be a reel or story (different format)")
                return None
            
            # Try each video URL
            for i, video_url in enumerate(video_urls, 1):
                try:
                    st.write(f"🔄 Attempting download from source {i}/{len(video_urls)}...")
                    
                    # Add referer header for Instagram
                    headers = self.headers.copy()
                    headers['Referer'] = 'https://www.instagram.com/'
                    headers['Sec-Fetch-Dest'] = 'video'
                    headers['Sec-Fetch-Mode'] = 'no-cors'
                    headers['Sec-Fetch-Site'] = 'cross-site'
                    
                    # Download the video
                    video_response = self.session.get(video_url, headers=headers, stream=True, timeout=60)
                    
                    if video_response.status_code == 200:
                        file_path = os.path.join(temp_dir, f'instagram_video_{timestamp}_{i}.mp4')
                        
                        # Download with progress
                        with open(file_path, 'wb') as f:
                            for chunk in video_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        # Verify download
                        if os.path.exists(file_path) and os.path.getsize(file_path) > 1024:
                            with open(file_path, 'rb') as f:
                                video_data = f.read()
                            
                            file_size_mb = len(video_data) / (1024 * 1024)
                            
                            # Clean up
                            try:
                                os.remove(file_path)
                            except:
                                pass
                            
                            st.success(f"✅ Successfully downloaded! Size: {file_size_mb:.1f} MB")
                            return video_data
                        else:
                            st.warning(f"Source {i} download incomplete, trying next...")
                    else:
                        st.warning(f"Source {i} failed with status {video_response.status_code}")
                    
                except Exception as e:
                    st.warning(f"Source {i} failed: {str(e)}")
                    continue
            
            # If all methods fail
            st.error("❌ All download attempts failed. Possible reasons:")
            st.write("• The video is private or requires login")
            st.write("• Instagram has updated their security")
            st.write("• The video format is not supported")
            st.write("• Network restrictions or firewall")
            
            return None
            
        except Exception as e:
            st.error(f"❌ Download failed: {str(e)}")
            return None

# ===== Streamlit UI =====
def main():
    st.markdown("""
    <div class="instagram-gradient">
        <h1>📥 Instagram Video Downloader PRO</h1>
        <p>Advanced Instagram Video Extraction • Multiple Methods • High Success Rate</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    <strong>🎯 Advanced Features:</strong>
    - 5+ different extraction methods
    - Automatic fallback when methods fail
    - Rotating user agents to avoid detection
    - Support for Reels, Posts, Stories, IGTV
    - Direct video URL extraction
    </div>
    """, unsafe_allow_html=True)

    # Initialize downloader
    if 'downloader' not in st.session_state:
        st.session_state.downloader = AdvancedInstagramDownloader()
    
    if 'video_data' not in st.session_state:
        st.session_state.video_data = None
    if 'video_info' not in st.session_state:
        st.session_state.video_info = None

    # Sidebar
    with st.sidebar:
        st.header("🎯 Extraction Methods")
        st.success("""
        1. **JSON-LD Data**
        2. **Script Tag Analysis**
        3. **Direct MP4 Search**
        4. **Shared Data Mining**
        5. **Video Versions Scan**
        """)
        
        
        
        st.markdown("---")
        if st.button("🔄 Clear Session", use_container_width=True):
            st.session_state.video_data = None
            st.session_state.video_info = None
            st.rerun()

    # Main content
    st.markdown("### 🔗 Paste Instagram Video URL")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        url = st.text_input(
            "Instagram URL:",
            placeholder="https://www.instagram.com/reel/... or https://www.instagram.com/p/...",
            label_visibility="collapsed"
        )
    
    with col2:
        st.write("")
        st.write("")
        if st.button("🚀 Download Video", use_container_width=True):
            if url and url.startswith('https://www.instagram.com/'):
                # Get video info first
                with st.spinner("🔍 Analyzing Instagram post..."):
                    info = st.session_state.downloader.get_video_info(url)
                    if info:
                        st.session_state.video_info = info
                        
                        # Then download video
                        with st.spinner("📥 Downloading video using multiple methods..."):
                            video_data = st.session_state.downloader.download_video(url)
                            if video_data:
                                st.session_state.video_data = video_data
                            else:
                                st.error("❌ Download failed with all methods")
                    else:
                        st.error("❌ Could not access this Instagram post")
            else:
                st.error("❌ Please enter a valid Instagram URL")

    # Display video information
    if st.session_state.video_info:
        info = st.session_state.video_info
        st.markdown("---")
        st.markdown("### 📊 Post Information")
        
        st.write(f"**Title:** {info['title']}")
        st.write(f"**URL:** {info['url']}")
        
        if st.session_state.video_data:
            st.success("**Status:** ✅ Video downloaded successfully!")
        else:
            st.warning("**Status:** ⚠️ Video not downloaded yet")

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
        
        file_size_mb = len(st.session_state.video_data) / (1024 * 1024)
        
        st.download_button(
            label=f"⬇️ Download Video ({file_size_mb:.1f} MB)",
            data=st.session_state.video_data,
            file_name=filename,
            mime="video/mp4",
            use_container_width=True,
            key="download_btn"
        )

    # Troubleshooting section
    st.markdown("---")
    with st.expander("🔧 Troubleshooting Guide"):
        st.markdown("""
        **If downloads fail:**
        
        1. **Check URL Format**: Make sure it's a direct Instagram post URL
        2. **Video Privacy**: Only public videos can be downloaded
        3. **Try Different Post**: Some posts might have different formats
        4. **Wait & Retry**: Instagram might temporarily block requests
        5. **Network Issues**: Check your internet connection
        
        **Supported URL formats:**
        - `https://www.instagram.com/reel/ABC123/`
        - `https://www.instagram.com/p/XYZ789/`
        - `https://www.instagram.com/tv/DEF456/`
        """)

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Advanced Instagram Video Downloader • For personal use only"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()