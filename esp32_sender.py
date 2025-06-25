import requests
import json
from typing import Dict, List, Optional
import time

class ESP32DataSender:
    def __init__(self, esp32_ip: str = "192.168.1.100", esp32_port: int = 80):
        """
        Initialize ESP32 data sender
        
        Args:
            esp32_ip: IP address of your ESP32
            esp32_port: Port number ESP32 is listening on
        """
        self.esp32_ip = esp32_ip
        self.esp32_port = esp32_port
        self.base_url = f"http://{esp32_ip}:{esp32_port}"
        
    def calculate_cart_environmental_impact(self, cart_items: List[Dict], db) -> Dict:
        """
        Calculate total environmental impact from cart items
        
        Args:
            cart_items: List of cart items from session
            db: Database connection object
            
        Returns:
            Dict with total water, carbon, energy values
        """
        totals = {
            'water_usage': 0.0,
            'carbon_footprint': 0.0, 
            'energy_usage': 0.0,
            'item_count': len(cart_items),
            'items': []
        }
        
        for cart_item in cart_items:
            qr_code = cart_item.get('qr_code')
            if not qr_code:
                continue
                
            # Get item details
            item = db.get_clothing_item(qr_code)
            if not item:
                continue
                
            materials = db.get_material_composition(qr_code)
            if not materials:
                continue
            
            item_impacts = {
                'name': cart_item.get('name', item['item_name']),
                'water_usage': 0.0,
                'carbon_footprint': 0.0,
                'energy_usage': 0.0
            }
            
            # Calculate impacts for each category
            for category in ['water_usage', 'carbon_footprint', 'energy_usage']:
                category_total = 0.0
                
                for material in materials:
                    impact_data = db.get_environmental_impact(
                        material['material_name'], category
                    )
                    if impact_data:
                        material_impact = (
                            impact_data['impact_value'] * 
                            (material['percentage'] / 100) * 
                            (item['weight_grams'] / 1000)
                        )
                        category_total += material_impact
                
                item_impacts[category] = round(category_total, 2)
                totals[category] += category_total
            
            totals['items'].append(item_impacts)
        
        # Round totals
        totals['water_usage'] = round(totals['water_usage'], 2)
        totals['carbon_footprint'] = round(totals['carbon_footprint'], 2)
        totals['energy_usage'] = round(totals['energy_usage'], 2)
        
        return totals
    
    def send_to_esp32(self, data: Dict, endpoint: str = "/data") -> Dict:
        """
        Send data to ESP32
        
        Args:
            data: Dictionary containing the data to send
            endpoint: ESP32 endpoint to send data to
            
        Returns:
            Response status and message
        """
        try:
            url = f"{self.base_url}{endpoint}"
            
            # Prepare the payload
            payload = {
                'timestamp': int(time.time()),
                'water_liters': data['water_usage'],
                'carbon_kg': data['carbon_footprint'], 
                'energy_mj': data['energy_usage'],
                'item_count': data['item_count'],
                'items': data['items']
            }
            
            print(f"Sending to ESP32 at {url}: {payload}")
            
            # Send POST request to ESP32
            response = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10  # 10 second timeout
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Data sent successfully to ESP32',
                    'esp32_response': response.text
                }
            else:
                return {
                    'success': False,
                    'message': f'ESP32 responded with status {response.status_code}',
                    'esp32_response': response.text
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'message': 'Timeout: ESP32 did not respond within 10 seconds'
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': f'Connection error: Could not reach ESP32 at {self.base_url}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error sending data to ESP32: {str(e)}'
            }
    
    def send_simple_values(self, water: float, carbon: float, energy: float) -> Dict:
        """
        Send just the three main values to ESP32
        
        Args:
            water: Water usage in liters
            carbon: Carbon footprint in kg CO2
            energy: Energy usage in MJ
        """
        simple_data = {
            'water_usage': water,
            'carbon_footprint': carbon,
            'energy_usage': energy,
            'item_count': 1,
            'items': []
        }
        
        return self.send_to_esp32(simple_data, "/simple")
    
    def test_connection(self) -> Dict:
        """Test if ESP32 is reachable"""
        try:
            response = requests.get(f"{self.base_url}/ping", timeout=5)
            return {
                'success': True,
                'message': 'ESP32 is reachable',
                'response': response.text
            }
        except:
            return {
                'success': False,
                'message': 'ESP32 is not reachable'
            }