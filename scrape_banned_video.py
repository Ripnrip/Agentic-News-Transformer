import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import json
import os
import subprocess
from env_validator import validate_conda_env

def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ]
    return random.choice(user_agents)

def kill_chrome_processes():
    try:
        subprocess.run(['pkill', 'Chrome'])
        time.sleep(2)
    except Exception as e:
        print(f"Error killing Chrome processes: {e}")

def wait_for_user_action():
    input("Please complete the Cloudflare verification and press Enter to continue...")

def wait_for_page_load(driver, timeout=30):
    try:
        # Wait for Cloudflare challenge to disappear
        WebDriverWait(driver, timeout).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#challenge-running, #challenge-stage"))
        )
        # Wait for main content
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body > div"))
        )
    except Exception as e:
        print(f"Page load wait error: {e}")
        return False
    return True

def _attempt_get_video_links(url):
    # Kill any existing Chrome processes
    kill_chrome_processes()
    
    options = uc.ChromeOptions()
    
    # Use your existing Chrome profile
    chrome_profile = os.path.expanduser('~/Library/Application Support/Google/Chrome')
    options.add_argument(f'--user-data-dir={chrome_profile}')
    options.add_argument('--profile-directory=Default')
    
    # Basic configuration
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-agent={get_random_user_agent()}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Add debugging options
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    print("Initializing Chrome...")
    try:
        driver = uc.Chrome(
            options=options,
            driver_executable_path=None,
            suppress_welcome=True,
            use_subprocess=True
        )
    except Exception as e:
        print(f"Error initializing Chrome: {e}")
        raise
    
    try:
        print(f"Navigating to {url}...")
        driver.get(url)
        
        print("\nWaiting for Cloudflare verification...")
        print("Please complete the verification in the browser window.")
        wait_for_user_action()
        
        print("Waiting for page to fully load...")
        if not wait_for_page_load(driver):
            print("Page load may not be complete, but continuing...")
        
        # Verify we're on the right page
        current_url = driver.current_url
        print(f"Current URL: {current_url}")
        
        if "banned.video" not in current_url:
            print("Navigation failed. Please check the browser.")
            wait_for_user_action()
        
        print("Starting content extraction...")
        fetched_video_links = set()
        scroll_position = 0
        last_count = 0
        no_new_content_count = 0
        
        while no_new_content_count < 3:
            # Scroll smoothly
            scroll_step = random.randint(100, 300)
            scroll_position += scroll_step
            driver.execute_script(f"window.scrollTo(0, {scroll_position});")
            time.sleep(random.uniform(1.5, 2.5))
            
            # Find video links
            elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='video'], a[href*='watch']")
            for element in elements:
                try:
                    href = element.get_attribute("href")
                    if href and ('video' in href.lower() or 'watch' in href.lower()):
                        fetched_video_links.add(href)
                except:
                    continue
            
            current_count = len(fetched_video_links)
            if current_count == last_count:
                no_new_content_count += 1
            else:
                no_new_content_count = 0
                print(f"Found {current_count} unique video links...")
            
            last_count = current_count
        
        video_links = list(fetched_video_links)
        print(f"\nExtraction complete. Found {len(video_links)} unique video links.")
        
        # Open first 10 videos in new tabs
        print("\nOpening first 10 videos in new tabs...")
        main_window = driver.current_window_handle
        
        for idx, video_link in enumerate(video_links[:10]):
            print(f"\nOpening video {idx + 1}: {video_link}")
            # Open new tab using JavaScript
            driver.execute_script(f'''window.open("{video_link}","_blank");''')
            time.sleep(2)
        
        # Get all window handles
        all_handles = driver.window_handles
        print(f"Opened {len(all_handles)-1} new tabs")
        
        # Switch to each new tab and click download
        for idx, handle in enumerate(all_handles[1:], 1):  # Skip the first handle (main window)
            try:
                print(f"\nProcessing tab {idx}")
                driver.switch_to.window(handle)
                time.sleep(3)  # Wait for page load
                
                print("Looking for download link...")
                try:
                    # Wait for and find the download link ending with .mp4
                    download_link = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR, 
                            "a[href$='.mp4'], a[href*='download.assets.video'][href$='true']"
                        ))
                    )
                    
                    print("Found download link...")
                    # Scroll element to middle of viewport
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center', inline: 'center'});", 
                        download_link
                    )
                    time.sleep(1)
                    
                    # Get the actual download URL
                    download_url = download_link.get_attribute('href')
                    print(f"Download URL: {download_url}")
                    
                    # Click using JavaScript
                    driver.execute_script("arguments[0].click();", download_link)
                    print("Download started")
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"Could not find or click download link: {e}")
                    # Try alternative method
                    try:
                        print("Trying alternative method...")
                        # Find link by href pattern
                        script = """
                        return Array.from(document.querySelectorAll('a')).find(
                            a => a.href && (a.href.endsWith('.mp4') || 
                                (a.href.includes('download.assets.video') && 
                                 a.href.endsWith('true')))
                        );
                        """
                        download_link = driver.execute_script(script)
                        if download_link:
                            driver.execute_script("arguments[0].click();", download_link)
                            print("Alternative method succeeded")
                    except Exception as e:
                        print(f"Alternative method failed: {e}")
                
            except Exception as e:
                print(f"Error processing tab {idx}: {e}")
        
        print("\nAll tabs processed")
        print("Please check the downloads in each tab")
        input("Press Enter when you're done with the downloads...")
        
        return video_links

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise

    finally:
        print("Keeping browser open for downloads...")
        pass

def get_video_links(url, retry_count=3):
    for attempt in range(retry_count):
        try:
            return _attempt_get_video_links(url)
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < retry_count - 1:
                wait_time = random.uniform(5, 10)
                print(f"Waiting {wait_time:.2f} seconds before retrying...")
                time.sleep(wait_time)
            else:
                raise

def save_links_to_file(links, filename="video_links.json"):
    try:
        with open(filename, 'w') as f:
            json.dump({"video_links": links}, f, indent=2)
        print(f"Links saved to {filename}")
    except Exception as e:
        print(f"Error saving links to file: {str(e)}")

def main():
    # Validate conda environment
    validate_conda_env()
    
    website_url = "https://banned.video/channel/most-banned-videos"
    
    print("Starting video link extraction...")
    print("Note: Using your existing Chrome profile")
    
    try:
        fetched_video_links = get_video_links(website_url)
        
        print("\nFound video links:")
        for idx, video_link in enumerate(fetched_video_links, 1):
            print(f"{idx}. {video_link}")
        
        save_links_to_file(fetched_video_links)
        print("\nBrowser remains open for downloads. Close it manually when finished.")
        
    except Exception as e:
        print(f"Script failed: {str(e)}")

if __name__ == "__main__":
    main()
