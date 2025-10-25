import streamlit as st
import yt_dlp
import os
import re
import tempfile
import time
import glob
from urllib.parse import urlparse

# Configure Streamlit page
st.set_page_config(
    page_title="Social Media Video Downloader",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== Custom CSS =====
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        background-color: #d4edda;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #28a745;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ffc107;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ===== Utility Functions =====
def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def is_supported_platform(url):
    supported_domains = [
        'facebook.com', 'fb.watch', 'instagram.com', 'instagr.am',
        'youtube.com', 'youtu.be', 'tiktok.com', 'twitter.com',
        'x.com', 'reddit.com'
    ]
    return any(domain in url.lower() for domain in supported_domains)

def get_video_info(url):
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True,
        'extract_flat': False
    }
    
    # Instagram-specific options
    if 'instagram.com' in url.lower():
        ydl_opts.update({
            'extract_flat': False,
        })
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        st.error(f"Error extracting video info: {str(e)}")
        return None

def download_video(url, quality='best'):
    temp_dir = tempfile.gettempdir()
    timestamp = int(time.time())
    
    try:
        format_selection = 'best[height<=720]/best' if quality == 'best' else 'worst'
        
        # Base options for all platforms
        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, f'download_{timestamp}.%(ext)s'),
            'format': format_selection,
            'quiet': True,
            'no_warnings': True,
            'nooverwrites': True,
        }
        
        # Instagram-specific options to handle rate limits
        if 'instagram.com' in url.lower():
            ydl_opts.update({
                'format': 'best',
                'extract_flat': False,
                'sleep_interval': 2,  # Add delay between requests
                'max_sleep_interval': 5,
                'retries': 10,  # More retries for Instagram
                'fragment_retries': 10,
                'skip_unavailable_fragments': True,
            })
        
        downloaded_files = []
        
        def progress_hook(d):
            if d['status'] == 'finished':
                if 'filename' in d:
                    downloaded_files.append(d['filename'])
        
        ydl_opts['progress_hooks'] = [progress_hook]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if downloaded_files:
            video_path = downloaded_files[0]
            if os.path.exists(video_path) and os.path.getsize(video_path) > 1024:
                with open(video_path, 'rb') as f:
                    video_data = f.read()
                
                # Clean up
                try:
                    os.remove(video_path)
                except:
                    pass
                
                return video_data
        
        return None
        
    except Exception as e:
        error_msg = str(e)
        
        # Handle Instagram-specific errors
        if 'instagram.com' in url.lower():
            if 'rate-limit' in error_msg.lower() or 'login required' in error_msg.lower():
                st.error("""
                ❌ Instagram Rate Limit Reached
                
                **Solutions to try:**
                - Wait 1-2 hours and try again
                - Try a different Instagram video
                - Use YouTube, TikTok, or other platforms instead
                - Instagram often blocks automated downloads
                """)
            else:
                st.error(f"Instagram error: {error_msg}")
        else:
            st.error(f"Download failed: {error_msg}")
        
        # Clean up any partial files
        for pattern in [f'download_{timestamp}.*', f'*{timestamp}*']:
            for file_path in glob.glob(os.path.join(temp_dir, pattern)):
                try:
                    os.remove(file_path)
                except:
                    pass
        return None

# ===== Streamlit UI =====
def main():
    st.markdown('<h1 class="main-header">📥 Social Media Video Downloader</h1>', unsafe_allow_html=True)

    # Platform limitations info
    st.markdown("""
    <div class="warning-box">
    <strong>⚠️ Platform Limitations:</strong>
    - <strong>Instagram:</strong> May have rate limits and require waiting between downloads
    - <strong>YouTube:</strong> Most reliable
    - <strong>TikTok:</strong> Usually works well
    - <strong>Facebook/Reddit:</strong> May require authentication for some content
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("About")
        st.write("""
        Download videos from:
        - ✅ YouTube (Best)
        - ✅ TikTok (Good)
        - ⚠️ Instagram (Rate Limited)
        - ⚠️ Facebook (Some limits)
        - ✅ Twitter/X
        - ✅ Reddit
        """)

        st.markdown("---")
        st.header("Tips for Success")
        st.info("""
        - **For Instagram:** Try again after 1-2 hours if rate limited
        - **Use YouTube/TikTok** for most reliable downloads
        - **Private videos** won't work
        - **Large videos** take longer to download
        """)

        if st.button("🔄 Clear Session"):
            st.session_state.clear()
            st.rerun()

    # Initialize session state
    if 'video_info' not in st.session_state:
        st.session_state.video_info = None
    if 'download_data' not in st.session_state:
        st.session_state.download_data = None

    st.markdown("### 🔗 Enter Video URL")
    url = st.text_input(
        "Paste Video URL:",
        placeholder="https://www.youtube.com/watch?v=... or https://tiktok.com/...",
        label_visibility="collapsed"
    )

    if url:
        if not is_valid_url(url):
            st.error("❌ Please enter a valid URL.")
        elif not is_supported_platform(url):
            st.warning("⚠️ This platform might not be supported.")
        else:
            # Show platform-specific info
            if 'instagram.com' in url.lower():
                st.warning("⚠️ Instagram: May have rate limits. If download fails, try again later.")
            elif 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
                st.success("✅ YouTube: Usually works well!")
            elif 'tiktok.com' in url.lower():
                st.success("✅ TikTok: Usually works well!")
            else:
                st.success("✅ Valid URL detected!")

    quality = st.selectbox(
        "Select Video Quality:",
        ["Best Available", "Lowest Quality"],
        index=0
    )

    # Buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Get Video Info", width='stretch'):
            if not url or not is_valid_url(url):
                st.error("Please enter a valid URL.")
            else:
                with st.spinner("Fetching video information..."):
                    info = get_video_info(url)
                    if info:
                        st.session_state.video_info = info
                        st.success("✅ Video info retrieved successfully!")
                    else:
                        st.error("❌ Could not fetch video info.")

    with col2:
        if st.button("💾 Download Video", width='stretch'):
            if not url or not is_valid_url(url):
                st.error("Please enter a valid URL first.")
            else:
                with st.spinner("Downloading video... This may take a while..."):
                    q = 'best' if quality == "Best Available" else 'worst'
                    video_data = download_video(url, q)
                    
                    if video_data:
                        st.session_state.download_data = video_data
                        file_size_mb = len(video_data) / (1024 * 1024)
                        st.success(f"✅ Downloaded successfully! File size: {file_size_mb:.1f} MB")
                    else:
                        # Error message is already shown in download_video function
                        pass

    # Video Info Display
    if st.session_state.video_info:
        info = st.session_state.video_info
        st.markdown("---")
        st.markdown("### 📊 Video Information")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.write(f"**Title:** {info.get('title', 'N/A')}")
            st.write(f"**Uploader:** {info.get('uploader', 'N/A')}")
            
            duration = info.get('duration', 'N/A')
            if duration != 'N/A':
                minutes, seconds = divmod(duration, 60)
                hours, minutes = divmod(minutes, 60)
                if hours > 0:
                    st.write(f"**Duration:** {int(hours)}:{int(minutes):02d}:{int(seconds):02d}")
                else:
                    st.write(f"**Duration:** {int(minutes)}:{int(seconds):02d}")
            else:
                st.write(f"**Duration:** {duration}")
                
            st.write(f"**Views:** {info.get('view_count', 'N/A')}")
            st.write(f"**Platform:** {info.get('extractor', 'N/A').title()}")

        with col2:
            thumbnail = info.get('thumbnail')
            if thumbnail:
                st.image(thumbnail, caption="Thumbnail", use_container_width=True)

    # Download Section
    if st.session_state.get("download_data"):
        st.markdown("---")
        st.markdown("### 💾 Save Video")
        
        info = st.session_state.video_info or {}
        title = info.get('title', 'downloaded_video')
        
        # Create safe filename
        safe_title = re.sub(r'[^\w\s-]', '', title)
        safe_title = re.sub(r'[-\s]+', '_', safe_title).strip('_')
        filename = f"{safe_title}.mp4"
        
        st.download_button(
            label="⬇️ Save Video File",
            data=st.session_state.download_data,
            file_name=filename,
            mime="video/mp4",
            width='stretch',
        )

    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "For educational use only • Respect platform terms of service"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()