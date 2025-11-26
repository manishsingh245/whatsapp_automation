import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import re

# === Step 1: Read Excel ===
data = pd.read_excel("RAW_data.xlsx")

# Check available columns
print("📋 Available columns in Excel:")
print(data.columns.tolist())
print()

# Clean column names (remove spaces)
data.columns = data.columns.str.strip().str.lower()

# Handle different possible column names
if 'number' not in data.columns:
    possible_names = ['phone', 'contact', 'mobile', 'telephone', 'phonenumber', 'phone number']
    column_found = None
    
    for col in data.columns:
        if col in possible_names or 'phone' in col or 'number' in col or 'contact' in col:
            column_found = col
            break
    
    if column_found:
        print(f"⚠️  'number' column not found. Using '{column_found}' instead.")
        data['number'] = data[column_found]
    else:
        print(f"⚠️  No phone number column found. Using first column: '{data.columns[0]}'")
        data['number'] = data[data.columns[0]]
    print()

# Clean the 'number' column thoroughly
data['number'] = data['number'].astype(str)
# Remove ALL non-digit characters except +
data['number'] = data['number'].str.replace(r'[^\d+]', '', regex=True)

# Fix numbers that are too long (remove trailing zeros or extra digits)
def fix_number(num):
    if num.startswith('+1') and len(num) > 12:
        return num[:12]  # US/Canada: +1 + 10 digits
    elif num.startswith('+') and len(num) > 15:
        return num[:15]
    return num

data['number'] = data['number'].apply(fix_number)

# Remove empty or invalid numbers
data = data[data['number'].str.len() > 5]
data = data[data['number'] != 'nan']

print("📋 Loaded numbers from Excel:")
for i, num in enumerate(data['number'].tolist(), 1):
    print(f"  {i}. {num}")
print()

if len(data) == 0:
    print("❌ No valid phone numbers found in Excel file!")
    exit()

# === Step 2: Setup Chrome + WhatsApp Web ===
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

driver.get("https://web.whatsapp.com")
print("🔐 Scan the QR code (if not logged in already)...")
time.sleep(35)

# Wait for WhatsApp to fully load
try:
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
    )
    print("✅ WhatsApp Web loaded successfully!\n")
except:
    print("❌ WhatsApp Web failed to load. Please check your connection.")
    driver.quit()
    exit()

# === Step 3: Message Template ===
message = '''Hi Greetings from Innovacio Technologies Pvt. Ltd.!

With 7 years of experience, we have successfully delivered projects across domains — including AI-driven platforms, fintech dashboards, healthtech apps, learning management systems, mobile apps and enterprise automation tools.

Our Project Expertise:
• AI LLM & RAG
• AI App & Web
• Generative AI
• AI Agent Development
• AI Detection
• Data Science

Our Core Skills:
We specialize in AI, LLMs, Machine learning, Node.js, React, React Native, Next.js, JavaScript, Python, MySQL, MongoDB, SQL, and Machine Learning — enabling us to build intelligent, scalable, and high-performing digital solutions.

Our Services:
• We provide dedicated software developers and full-cycle development teams for:
• Custom AI Solutions
• Web & Mobile Applications
• Enterprise Automation Platforms

Would you be open to a quick consultation call this week?

Innovacio Technologies Pvt Ltd.'''.strip()

# === Step 4: Loop through contacts ===
results = []
success_count = 0
failed_count = 0

for index, row in data.iterrows():
    number = str(row['number']).strip()
    
    # Skip empty numbers
    if not number or number == 'nan':
        continue
    
    print(f"📞 Processing [{index+1}/{len(data)}]: {number}")
    
    # Check if driver is still alive
    try:
        _ = driver.current_url
    except:
        print("❌ Browser crashed! Restarting...")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        driver.get("https://web.whatsapp.com")
        print("Please scan QR code again...")
        time.sleep(30)
    
    url = f"https://web.whatsapp.com/send?phone={number}"
    
    try:
        driver.get(url)
        time.sleep(10)  # Increased wait time
        
        # Check for invalid number alert - multiple ways
        invalid_number = False
        
        # Method 1: Check for "Phone number shared via url is invalid" text
        try:
            invalid_alert = driver.find_element(By.XPATH, '//*[contains(text(), "Phone number shared via url is invalid")]')
            invalid_number = True
            print(f"   ❌ Invalid/Not on WhatsApp\n")
            results.append({"number": number, "status": "Invalid/Not on WhatsApp"})
            failed_count += 1
            continue
        except:
            pass
        
        # Method 2: Wait for message input box (multiple possible selectors)
        message_box = None
        selectors = [
            '//div[@contenteditable="true"][@data-tab="10"]',
            '//div[@contenteditable="true"][@role="textbox"]',
            '//div[@title="Type a message"]',
            '//div[@contenteditable="true"][@data-lexical-editor="true"]',
            '//p[@class="selectable-text copyable-text"]',
            '//footer//div[@contenteditable="true"]'
        ]
        
        for selector in selectors:
            try:
                message_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                print(f"   📝 Found message box")
                break
            except:
                continue
        
        if not message_box:
            print(f"   ❌ Could not find message box - Invalid/Not on WhatsApp\n")
            results.append({"number": number, "status": "Invalid/Not on WhatsApp"})
            failed_count += 1
            continue
        
        # Click and type message
        message_box.click()
        time.sleep(2)
        
        # Send message line by line
        lines = message.split("\n")
        for i, line in enumerate(lines):
            if line.strip():  # Only send non-empty lines
                message_box.send_keys(line)
            if i < len(lines) - 1:
                message_box.send_keys(Keys.SHIFT + Keys.ENTER)
        
        time.sleep(2)
        message_box.send_keys(Keys.ENTER)
        
        print(f"   ✅ Message sent successfully!\n")
        results.append({"number": number, "status": "Success"})
        success_count += 1
        time.sleep(8)  # Increased delay to avoid rate limiting
        
    except Exception as e:
        error_msg = str(e)[:100]
        print(f"   ❌ Failed: {error_msg}\n")
        results.append({"number": number, "status": f"Error: {error_msg}"})
        failed_count += 1
        time.sleep(3)

# === Step 5: Save Results ===
if results:
    results_df = pd.DataFrame(results)
    results_df.to_excel("message_results.xlsx", index=False)
    print("\n" + "="*50)
    print("🎉 All messages processed!")
    print("="*50)
    print(f"📊 Results saved to 'message_results.xlsx'")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed/Invalid: {failed_count}")
    print(f"📝 Total: {len(results)}")
    print("="*50)
else:
    print("\n⚠️ No messages were processed!")

try:
    driver.quit()
except:
    pass

# import time
# import pandas as pd
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager
# import re

# # === Step 1: Read Excel ===
# data = pd.read_excel("RAW_data.xlsx")

# # Clean the 'number' column thoroughly
# data['number'] = data['number'].astype(str)
# # Remove ALL non-digit characters except +
# data['number'] = data['number'].str.replace(r'[^\d+]', '', regex=True)

# # Fix numbers that are too long (remove trailing zeros or extra digits)
# def fix_number(num):
#     if num.startswith('+1') and len(num) > 12:
#         return num[:12]  # US/Canada: +1 + 10 digits
#     elif num.startswith('+') and len(num) > 15:
#         return num[:15]
#     return num

# data['number'] = data['number'].apply(fix_number)

# print("📋 Loaded numbers from Excel:")
# for i, num in enumerate(data['number'].tolist(), 1):
#     print(f"  {i}. {num}")
# print()

# # === Step 2: Setup Chrome + WhatsApp Web ===
# chrome_options = Options()
# chrome_options.add_argument("--start-maximized")
# chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--disable-dev-shm-usage")
# chrome_options.add_argument("--disable-gpu")
# chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

# driver = webdriver.Chrome(
#     service=Service(ChromeDriverManager().install()),
#     options=chrome_options
# )

# driver.get("https://web.whatsapp.com")
# print("🔐 Scan the QR code (if not logged in already)...")
# time.sleep(35)

# # Wait for WhatsApp to fully load
# try:
#     WebDriverWait(driver, 60).until(
#         EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
#     )
#     print("✅ WhatsApp Web loaded successfully!\n")
# except:
#     print("❌ WhatsApp Web failed to load. Please check your connection.")
#     driver.quit()
#     exit()

# # === Step 3: Message Template ===
# message = '''Hi Greetings from Innovacio Technologies Pvt. Ltd.!

# With 7 years of experience, we have successfully delivered projects across domains — including AI-driven platforms, fintech dashboards, healthtech apps, learning management systems, mobile apps and enterprise automation tools.

# Our Project Expertise:
# • AI LLM & RAG
# • AI App & Web
# • Generative AI
# • AI Agent Development
# • AI Detection
# • Data Science

# Our Core Skills:
# We specialize in AI, LLMs, Machine learning, Node.js, React, React Native, Next.js, JavaScript, Python, MySQL, MongoDB, SQL, and Machine Learning — enabling us to build intelligent, scalable, and high-performing digital solutions.

# Our Services:
# • We provide dedicated software developers and full-cycle development teams for:
# • Custom AI Solutions
# • Web & Mobile Applications
# • Enterprise Automation Platforms

# Would you be open to a quick consultation call this week?

# Innovacio Technologies Pvt Ltd.'''.strip()

# # === Step 4: Loop through contacts ===
# results = []
# success_count = 0
# failed_count = 0

# for index, row in data.iterrows():
#     number = str(row['number']).strip()
    
#     # Skip empty numbers
#     if not number or number == 'nan':
#         continue
    
#     print(f"📞 Processing [{index+1}/{len(data)}]: {number}")
    
#     # Check if driver is still alive
#     try:
#         _ = driver.current_url
#     except:
#         print("❌ Browser crashed! Restarting...")
#         driver = webdriver.Chrome(
#             service=Service(ChromeDriverManager().install()),
#             options=chrome_options
#         )
#         driver.get("https://web.whatsapp.com")
#         print("Please scan QR code again...")
#         time.sleep(30)
    
#     url = f"https://web.whatsapp.com/send?phone={number}"
    
#     try:
#         driver.get(url)
#         time.sleep(10)  # Increased wait time
        
#         # Check for invalid number alert - multiple ways
#         invalid_number = False
        
#         # Method 1: Check for "Phone number shared via url is invalid" text
#         try:
#             invalid_alert = driver.find_element(By.XPATH, '//*[contains(text(), "Phone number shared via url is invalid")]')
#             invalid_number = True
#             print(f"   ❌ Invalid/Not on WhatsApp\n")
#             results.append({"number": number, "status": "Invalid/Not on WhatsApp"})
#             failed_count += 1
#             continue
#         except:
#             pass
        
#         # Method 2: Wait for message input box (multiple possible selectors)
#         message_box = None
#         selectors = [
#             '//div[@contenteditable="true"][@data-tab="10"]',
#             '//div[@contenteditable="true"][@role="textbox"]',
#             '//div[@title="Type a message"]',
#             '//div[@contenteditable="true"][@data-lexical-editor="true"]',
#             '//p[@class="selectable-text copyable-text"]',
#             '//footer//div[@contenteditable="true"]'
#         ]
        
#         for selector in selectors:
#             try:
#                 message_box = WebDriverWait(driver, 10).until(
#                     EC.presence_of_element_located((By.XPATH, selector))
#                 )
#                 print(f"   📝 Found message box with selector: {selector[:50]}...")
#                 break
#             except:
#                 continue
        
#         if not message_box:
#             print(f"   ❌ Could not find message box - Invalid/Not on WhatsApp\n")
#             results.append({"number": number, "status": "Invalid/Not on WhatsApp"})
#             failed_count += 1
#             continue
        
#         # Click and type message
#         message_box.click()
#         time.sleep(2)
        
#         # Send message line by line
#         lines = message.split("\n")
#         for i, line in enumerate(lines):
#             if line.strip():  # Only send non-empty lines
#                 message_box.send_keys(line)
#             if i < len(lines) - 1:
#                 message_box.send_keys(Keys.SHIFT + Keys.ENTER)
        
#         time.sleep(2)
#         message_box.send_keys(Keys.ENTER)
        
#         print(f"   ✅ Message sent successfully!\n")
#         results.append({"number": number, "status": "Success"})
#         success_count += 1
#         time.sleep(8)  # Increased delay to avoid rate limiting
        
#     except Exception as e:
#         error_msg = str(e)[:100]
#         print(f"   ❌ Failed: {error_msg}\n")
#         results.append({"number": number, "status": f"Error: {error_msg}"})
#         failed_count += 1
#         time.sleep(3)

# # === Step 5: Save Results ===
# if results:
#     results_df = pd.DataFrame(results)
#     results_df.to_excel("message_results.xlsx", index=False)
#     print("\n" + "="*50)
#     print("🎉 All messages processed!")
#     print("="*50)
#     print(f"📊 Results saved to 'message_results.xlsx'")
#     print(f"✅ Successful: {success_count}")
#     print(f"❌ Failed/Invalid: {failed_count}")
#     print(f"📝 Total: {len(results)}")
#     print("="*50)
# else:
#     print("\n⚠️ No messages were processed!")

# try:
#     driver.quit()
# except:
#     pass
# import time
# import pandas as pd
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager
# import re

# # === Step 1: Read Excel ===
# data = pd.read_excel("RAW_data.xlsx")

# # Clean the 'number' column thoroughly
# data['number'] = data['number'].astype(str)
# # Remove ALL non-digit characters except +
# data['number'] = data['number'].str.replace(r'[^\d+]', '', regex=True)

# # Fix numbers that are too long (remove trailing zeros or extra digits)
# def fix_number(num):
#     if num.startswith('+1') and len(num) > 12:
#         return num[:12]  # US/Canada: +1 + 10 digits
#     elif num.startswith('+') and len(num) > 15:
#         return num[:15]
#     return num

# data['number'] = data['number'].apply(fix_number)

# print("📋 Loaded numbers from Excel:")
# for i, num in enumerate(data['number'].tolist(), 1):
#     print(f"  {i}. {num}")
# print()

# # === Step 2: Setup Chrome + WhatsApp Web ===
# chrome_options = Options()
# chrome_options.add_argument("--start-maximized")
# chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--disable-dev-shm-usage")
# chrome_options.add_argument("--disable-gpu")
# chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

# driver = webdriver.Chrome(
#     service=Service(ChromeDriverManager().install()),
#     options=chrome_options
# )

# driver.get("https://web.whatsapp.com")
# print("🔐 Scan the QR code (if not logged in already)...")
# time.sleep(35)

# # Wait for WhatsApp to fully load
# try:
#     WebDriverWait(driver, 60).until(
#         EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
#     )
#     print("✅ WhatsApp Web loaded successfully!\n")
# except:
#     print("❌ WhatsApp Web failed to load. Please check your connection.")
#     driver.quit()
#     exit()

# # === Step 3: Message Template ===
# message = '''Hi Greetings from Innovacio Technologies Pvt. Ltd.!

# With 7 years of experience, we have successfully delivered projects across domains — including AI-driven platforms, fintech dashboards, healthtech apps, learning management systems, mobile apps and enterprise automation tools.

# Our Project Expertise:
# • AI LLM & RAG
# • AI App & Web
# • Generative AI
# • AI Agent Development
# • AI Detection
# • Data Science

# Our Core Skills:
# We specialize in AI, LLMs, Machine learning, Node.js, React, React Native, Next.js, JavaScript, Python, MySQL, MongoDB, SQL, and Machine Learning — enabling us to build intelligent, scalable, and high-performing digital solutions.

# Our Services:
# • We provide dedicated software developers and full-cycle development teams for:
# • Custom AI Solutions
# • Web & Mobile Applications
# • Enterprise Automation Platforms

# Would you be open to a quick consultation call this week?

# Innovacio Technologies Pvt Ltd.'''.strip()

# # === Step 4: Loop through contacts ===
# results = []
# success_count = 0
# failed_count = 0

# for index, row in data.iterrows():
#     number = str(row['number']).strip()
    
#     # Skip empty numbers
#     if not number or number == 'nan':
#         continue
    
#     print(f"📞 Processing [{index+1}/{len(data)}]: {number}")
    
#     # Check if driver is still alive
#     try:
#         _ = driver.current_url
#     except:
#         print("❌ Browser crashed! Restarting...")
#         driver = webdriver.Chrome(
#             service=Service(ChromeDriverManager().install()),
#             options=chrome_options
#         )
#         driver.get("https://web.whatsapp.com")
#         print("Please scan QR code again...")
#         time.sleep(30)
    
#     url = f"https://web.whatsapp.com/send?phone={number}"
    
#     try:
#         driver.get(url)
#         time.sleep(8)
        
#         # Check for invalid number alert - multiple ways
#         invalid_number = False
        
#         # Method 1: Check for alert/popup
#         try:
#             alert = driver.find_element(By.XPATH, '//div[contains(text(), "Phone number shared via url is invalid")]')
#             invalid_number = True
#         except:
#             pass
        
#         # Method 2: Check page source
#         if not invalid_number:
#             try:
#                 page_text = driver.page_source.lower()
#                 if "phone number shared via url is invalid" in page_text or "invalid" in page_text:
#                     invalid_number = True
#             except:
#                 pass
        
#         # Method 3: Check if message box appears
#         if not invalid_number:
#             try:
#                 WebDriverWait(driver, 8).until(
#                     EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
#                 )
#             except:
#                 invalid_number = True
        
#         if invalid_number:
#             print(f"   ❌ Invalid/Not on WhatsApp\n")
#             results.append({"number": number, "status": "Invalid/Not on WhatsApp"})
#             failed_count += 1
#             continue
        
#         # Find message box
#         message_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
#         message_box.click()
#         time.sleep(1)
        
#         # Send message line by line
#         lines = message.split("\n")
#         for i, line in enumerate(lines):
#             message_box.send_keys(line)
#             if i < len(lines) - 1:
#                 message_box.send_keys(Keys.SHIFT + Keys.ENTER)
        
#         time.sleep(1)
#         message_box.send_keys(Keys.ENTER)
        
#         print(f"   ✅ Message sent successfully!\n")
#         results.append({"number": number, "status": "Success"})
#         success_count += 1
#         time.sleep(5)
        
#     except Exception as e:
#         error_msg = str(e)[:100]
#         print(f"   ❌ Failed: {error_msg}\n")
#         results.append({"number": number, "status": f"Error: {error_msg}"})
#         failed_count += 1
#         time.sleep(3)

# # === Step 5: Save Results ===
# if results:
#     results_df = pd.DataFrame(results)
#     results_df.to_excel("message_results.xlsx", index=False)
#     print("\n" + "="*50)
#     print("🎉 All messages processed!")
#     print("="*50)
#     print(f"📊 Results saved to 'message_results.xlsx'")
#     print(f"✅ Successful: {success_count}")
#     print(f"❌ Failed/Invalid: {failed_count}")
#     print(f"📝 Total: {len(results)}")
#     print("="*50)
# else:
#     print("\n⚠️ No messages were processed!")

# try:
#     driver.quit()
# except:
#     pass


# import time
# import pandas as pd
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager
# import re

# # === Step 1: Read Excel ===
# data = pd.read_excel("RAW_data.xlsx")

# # Clean the 'number' column - remove all unwanted characters
# data['number'] = data['number'].astype(str).str.replace(r'[^\d+]', '', regex=True)
# print("📋 Loaded numbers:")
# print(data['number'].tolist())
# print()

# # === Step 2: Setup Chrome + WhatsApp Web ===
# chrome_options = Options()
# chrome_options.add_argument("--start-maximized")
# chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--disable-dev-shm-usage")
# chrome_options.add_argument("--disable-gpu")
# chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

# driver = webdriver.Chrome(
#     service=Service(ChromeDriverManager().install()),
#     options=chrome_options
# )

# driver.get("https://web.whatsapp.com")
# print("🔐 Scan the QR code (if not logged in already)...")
# time.sleep(35)

# # Wait for WhatsApp to fully load
# try:
#     WebDriverWait(driver, 60).until(
#         EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
#     )
#     print("✅ WhatsApp Web loaded successfully!\n")
# except:
#     print("❌ WhatsApp Web failed to load. Please check your connection.")
#     driver.quit()
#     exit()

# # === Step 3: Message Template ===
# message = '''Hi Greetings from Innovacio Technologies Pvt. Ltd.!

# With 7 years of experience, we have successfully delivered projects across domains — including AI-driven platforms, fintech dashboards, healthtech apps, learning management systems, mobile apps and enterprise automation tools.

# Our Project Expertise:
# • AI LLM & RAG
# • AI App & Web
# • Generative AI
# • AI Agent Development
# • AI Detection
# • Data Science

# Our Core Skills:
# We specialize in AI, LLMs, Machine learning, Node.js, React, React Native, Next.js, JavaScript, Python, MySQL, MongoDB, SQL, and Machine Learning — enabling us to build intelligent, scalable, and high-performing digital solutions.

# Our Services:
# • We provide dedicated software developers and full-cycle development teams for:
# • Custom AI Solutions
# • Web & Mobile Applications
# • Enterprise Automation Platforms

# Would you be open to a quick consultation call this week?

# Innovacio Technologies Pvt Ltd.'''.strip()

# # === Step 4: Loop through contacts ===
# results = []
# success_count = 0
# failed_count = 0

# for index, row in data.iterrows():
#     number = str(row['number']).strip()
    
#     # Skip empty numbers
#     if not number or number == 'nan':
#         continue
    
#     print(f"📞 Processing [{index+1}/{len(data)}]: {number}")
    
#     # Check if driver is still alive
#     try:
#         _ = driver.current_url
#     except:
#         print("❌ Browser crashed! Restarting...")
#         driver = webdriver.Chrome(
#             service=Service(ChromeDriverManager().install()),
#             options=chrome_options
#         )
#         driver.get("https://web.whatsapp.com")
#         print("Please scan QR code again...")
#         time.sleep(30)
    
#     url = f"https://web.whatsapp.com/send?phone={number}"
    
#     try:
#         driver.get(url)
#         time.sleep(8)
        
#         # Check for invalid number alert - multiple ways
#         invalid_number = False
        
#         # Method 1: Check for alert/popup
#         try:
#             alert = driver.find_element(By.XPATH, '//div[contains(text(), "Phone number shared via url is invalid")]')
#             invalid_number = True
#         except:
#             pass
        
#         # Method 2: Check page source
#         if not invalid_number:
#             try:
#                 page_text = driver.page_source.lower()
#                 if "phone number shared via url is invalid" in page_text or "invalid" in page_text:
#                     invalid_number = True
#             except:
#                 pass
        
#         # Method 3: Check if message box appears
#         if not invalid_number:
#             try:
#                 WebDriverWait(driver, 8).until(
#                     EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
#                 )
#             except:
#                 invalid_number = True
        
#         if invalid_number:
#             print(f"   ❌ Invalid/Not on WhatsApp\n")
#             results.append({"number": number, "status": "Invalid/Not on WhatsApp"})
#             failed_count += 1
#             continue
        
#         # Find message box
#         message_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
#         message_box.click()
#         time.sleep(1)
        
#         # Send message line by line
#         lines = message.split("\n")
#         for i, line in enumerate(lines):
#             message_box.send_keys(line)
#             if i < len(lines) - 1:
#                 message_box.send_keys(Keys.SHIFT + Keys.ENTER)
        
#         time.sleep(1)
#         message_box.send_keys(Keys.ENTER)
        
#         print(f"   ✅ Message sent successfully!\n")
#         results.append({"number": number, "status": "Success"})
#         success_count += 1
#         time.sleep(5)
        
#     except Exception as e:
#         error_msg = str(e)[:100]
#         print(f"   ❌ Failed: {error_msg}\n")
#         results.append({"number": number, "status": f"Error: {error_msg}"})
#         failed_count += 1
#         time.sleep(3)

# # === Step 5: Save Results ===
# if results:
#     results_df = pd.DataFrame(results)
#     results_df.to_excel("message_results.xlsx", index=False)
#     print("\n" + "="*50)
#     print("🎉 All messages processed!")
#     print("="*50)
#     print(f"📊 Results saved to 'message_results.xlsx'")
#     print(f"✅ Successful: {success_count}")
#     print(f"❌ Failed/Invalid: {failed_count}")
#     print(f"📝 Total: {len(results)}")
#     print("="*50)
# else:
#     print("\n⚠️ No messages were processed!")

# try:
#     driver.quit()
# except:
#     pass

# import time
# import pandas as pd
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.keys import Keys
# from webdriver_manager.chrome import ChromeDriverManager

# # === Step 1: Read Excel ===

# data = pd.read_excel("RAW_data.xlsx")

# # === Step 2: Setup Chrome + WhatsApp Web ===
# chrome_options = Options()
# chrome_options.add_argument("--start-maximized")
# chrome_options.add_argument("--disable-gpu")
# chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--disable-dev-shm-usage")

# driver = webdriver.Chrome(
#     service=Service(ChromeDriverManager().install()),
#     options=chrome_options
# )
# driver.get("https://web.whatsapp.com")

# print("Scan the QR code (if not logged in already)...")
# time.sleep(30)

# # === Step 3: Loop through contacts ===
# for index, row in data.iterrows():
#     number = str(row['number'])
#     message = f'''
#         Technical Approach

#         1. Mobile App (React Native / iOS-first)

#         Framework: React Native (Expo) with offline-first architecture (SQLite + Redux-Persist).

#         Features:

#         Geo-tag + timestamp auto-capture on photo upload.
#     '''
#     url = f"https://web.whatsapp.com/send?phone={number}"
#     driver.get(url)
#     time.sleep(10)

#     try:
#         message_box = driver.find_element(By.XPATH, '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div/div[3]/div[1]/p')
#         message_box.send_keys(message)
#         time.sleep(5)
#         # send_btn = driver.find_element(By.XPATH, '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div/div[4]/div/span/div/div/div[1]/div[1]/span[1]')
#         # send_btn.click()
#         print(f"✅ Message sent to {number}")
#         time.sleep(5)
#     except Exception as e:
#         print(f"❌ Failed to send to {number}: {e}")

# print("🎉 All messages sent!")
# # driver.quit()




# import time
# import pandas as pd
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.keys import Keys
# from webdriver_manager.chrome import ChromeDriverManager

# # === Step 1: Read Excel ===

# data = pd.read_excel("RAW_data.xlsx")

# # === Step 2: Setup Chrome + WhatsApp Web ===
# chrome_options = Options()
# chrome_options.add_argument("--start-maximized")
# chrome_options.add_argument("--disable-gpu")
# chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--disable-dev-shm-usage")

# driver = webdriver.Chrome(
#     service=Service(ChromeDriverManager().install()),
#     options=chrome_options
# )
# driver.get("https://web.whatsapp.com")

# print("Scan the QR code (if not logged in already)...")
# time.sleep(30)

# # === Step 3: Loop through contacts ===
# for index, row in data.iterrows():
#     number = str(row['number'])
#     message = f'''
#         Technical Approach

#         1. Mobile App (React Native / iOS-first)

#         Framework: React Native (Expo) with offline-first architecture (SQLite + Redux-Persist).

#         Features:

#         Geo-tag + timestamp auto-capture on photo upload.
#     '''
#     url = f"https://web.whatsapp.com/send?phone={number}"
#     driver.get(url)
#     time.sleep(10)

#     try:
#         message_box = driver.find_element(By.XPATH, '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div/div[3]/div[1]/p')
#         message_box.send_keys(message)
#         time.sleep(5)
#         # send_btn = driver.find_element(By.XPATH, '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div/div[4]/div/span/div/div/div[1]/div[1]/span[1]')
#         # send_btn.click()
#         print(f"✅ Message sent to {number}")
#         time.sleep(5)
#     except Exception as e:
#         print(f"❌ Failed to send to {number}: {e}")

# print("🎉 All messages sent!")
# # driver.quit()

