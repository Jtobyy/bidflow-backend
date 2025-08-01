from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def verify_pecb_certificate(cert_number: str, last_name: str) -> dict:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run Chrome in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get("https://pecb.com/en/userCertification/certificateVerification")

    result_data = {}

    try:
        # Wait until form is ready
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "UserCertification_lastname")))

        # Fill in form
        driver.find_element(By.ID, "UserCertification_lastname").send_keys(last_name)
        driver.find_element(By.ID, "UserCertification_cert_number").send_keys(cert_number)
        driver.find_element(By.ID, "ajaxSubmitBtn").click()

        # Wait for result
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "result")))

        time.sleep(1)  # Give extra second for content to render

        rows = driver.find_elements(By.CSS_SELECTOR, "#user-certification-grid table tbody tr")
        if not rows or len(rows) == 0:
            return {
                "error": "No results found on PECB portal",
                "status": "Not Found"
            }
        try:
            cells = rows[0].find_elements(By.TAG_NAME, "td")
            result_data = {
                "first_name": cells[0].text,
                "last_name": cells[1].text,
                "certificate_title": cells[2].text,
                "certificate_number": cells[3].text,
                "issue_date": cells[4].text,
                "valid_upto": cells[5].text,
                "status": cells[6].text,
            }

            print("✅ Certificate Found:")
            for key, value in result_data.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
        except Exception as e:
            return {
                "error": f"Parsing error: {str(e)}",
                "status": "Parse Error"
            }

    except Exception as e:
        print("❌ Error verifying certificate:", str(e))
        result_data["error"] = str(e)

    finally:
        driver.quit()

    return result_data


# Example usage
if __name__ == "__main__":
    cert = "RMM1090452-2022-06"
    last = "KABISYAKI"
    verify_pecb_certificate(cert, last)
