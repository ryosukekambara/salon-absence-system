from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import time

class SalonBoardScraper:
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # バックグラウンド実行
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
    def login(self, username, password):
        """サロンボードにログイン"""
        try:
            self.driver.get('https://salonboard.com/login/')
            
            # ログイン情報入力
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "loginCd"))
            )
            username_field.send_keys(username)
            
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.send_keys(password)
            
            # ログインボタンクリック
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f"ログインエラー: {e}")
            return False
    
    def get_appointments(self, staff_name, date):
        """指定スタッフ・日付の予約取得"""
        try:
            # スケジュール画面へ
            url = f'https://salonboard.com/KLP/schedule/salonSchedule/?date={date}'
            self.driver.get(url)
            time.sleep(2)
            
            appointments = []
            
            # 予約情報を取得（実際のHTML構造に応じて調整）
            reservations = self.driver.find_elements(By.CLASS_NAME, "reservation-item")
            
            for reservation in reservations:
                try:
                    # スタッフ名確認
                    staff = reservation.find_element(By.CLASS_NAME, "staff-name").text
                    
                    if staff_name in staff:
                        appointment_data = {
                            "staff": staff,
                            "time": reservation.find_element(By.CLASS_NAME, "time").text,
                            "customer": reservation.find_element(By.CLASS_NAME, "customer-name").text,
                            "service": reservation.find_element(By.CLASS_NAME, "service").text,
                            "date": date
                        }
                        appointments.append(appointment_data)
                        
                except Exception as e:
                    continue
            
            return appointments
            
        except Exception as e:
            print(f"予約取得エラー: {e}")
            return []
    
    def close(self):
        """ブラウザを閉じる"""
        self.driver.quit()

# 使用例
def scrape_appointments(staff_name):
    scraper = SalonBoardScraper()
    
    if scraper.login("CD18317", "Ne8T2Hhi!"):
        today = datetime.now().strftime('%Y%m%d')
        appointments = scraper.get_appointments(staff_name, today)
        scraper.close()
        return appointments
    else:
        scraper.close()
        return []
