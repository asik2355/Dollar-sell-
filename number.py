import random
import time

class NumberManager:
    def __init__(self):
        # Mocking a list of countries and services
        self.countries = {
            "Bangladesh": "BD",
            "India": "IN",
            "USA": "US",
            "Russia": "RU",
            "Vietnam": "VN"
        }
        self.services = {
            "Telegram": "tg",
            "WhatsApp": "wa",
            "Facebook": "fb",
            "Google": "go",
            "TikTok": "tk"
        }
        self.active_numbers = {}

    def get_countries(self):
        return list(self.countries.keys())

    def get_services(self):
        return list(self.services.keys())

    def buy_number(self, country, service, user_id):
        # In a real app, you would call an API like 5sim.net or smspva.com here
        # Example API Call: 
        # response = requests.get(f"https://5sim.net/v1/user/buy/activation/{country}/{operator}/{service}")
        
        number_id = str(random.randint(100000, 999999))
        phone_number = f"+{random.randint(1, 999)}{random.randint(1000000, 9999999)}"
        
        number_data = {
            "id": number_id,
            "number": phone_number,
            "country": country,
            "service": service,
            "status": "WAITING_SMS",
            "otp": None,
            "start_time": time.time()
        }
        
        if user_id not in self.active_numbers:
            self.active_numbers[user_id] = []
        
        self.active_numbers[user_id].append(number_data)
        return number_data

    def check_otp(self, user_id, number_id):
        if user_id not in self.active_numbers:
            return None
        
        for item in self.active_numbers[user_id]:
            if item["id"] == number_id:
                # Simulate OTP arrival after a few seconds
                elapsed = time.time() - item["start_time"]
                if elapsed > 10 and not item["otp"]:
                    item["otp"] = str(random.randint(1000, 9999))
                    item["status"] = "FINISHED"
                return item
        return None

# Singleton instance
manager = NumberManager()
