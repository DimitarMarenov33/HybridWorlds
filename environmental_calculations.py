# environmental_calculations.py - Specific environmental impact calculations
"""
Clean calculation functions for environmental impacts using database data.
Focuses on specific metrics: water (liters), carbon (kg CO2), energy (MJ).
"""

from typing import Dict, List, Optional, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnvironmentalCalculator:
    """
    Calculator for specific environmental impacts using database data.
    Provides clean functions to get water usage, carbon footprint, and energy usage.
    """
    
    def __init__(self, db_connection):
        """
        Initialize with database connection.
        
        Args:
            db_connection: FashionEnvironmentDB instance
        """
        self.db = db_connection
    
    def calculate_water_usage_liters(self, qr_code: str) -> Dict:
        """
        Calculate total water usage in liters for a clothing item.
        
        Args:
            qr_code: QR code of the clothing item
            
        Returns:
            Dict with water usage data:
            {
                'total_liters': float,
                'unit': str,
                'breakdown': [list of material contributions],
                'item_weight_grams': int
            }
        """
        try:
            # Get clothing item details
            item = self.db.get_clothing_item(qr_code)
            if not item:
                return {'error': f'Item with QR code {qr_code} not found'}
            
            # Get material composition
            materials = self.db.get_material_composition(qr_code)
            if not materials:
                return {'error': f'No material composition found for {qr_code}'}
            
            total_water_liters = 0.0
            breakdown = []
            
            for material in materials:
                # Get water usage impact for this material
                impact_data = self.db.get_environmental_impact(
                    material['material_name'], 
                    'water_usage'
                )
                
                if impact_data:
                    # Calculate: impact_per_kg * material_percentage * item_weight_kg
                    material_water = (
                        impact_data['impact_value'] *  # L/kg
                        (material['percentage'] / 100) *  # percentage as decimal
                        (item['weight_grams'] / 1000)  # convert grams to kg
                    )
                    
                    total_water_liters += material_water
                    
                    breakdown.append({
                        'material': material['material_name'],
                        'percentage': material['percentage'],
                        'water_liters': round(material_water, 2),
                        'impact_per_kg': impact_data['impact_value']
                    })
                else:
                    logger.warning(f"No water usage data for material: {material['material_name']}")
                    breakdown.append({
                        'material': material['material_name'],
                        'percentage': material['percentage'],
                        'water_liters': 0.0,
                        'impact_per_kg': 0.0,
                        'note': 'No impact data available'
                    })
            
            return {
                'total_liters': round(total_water_liters, 2),
                'unit': 'liters',
                'breakdown': breakdown,
                'item_weight_grams': item['weight_grams'],
                'item_name': item['item_name']
            }
            
        except Exception as e:
            logger.error(f"Error calculating water usage for {qr_code}: {str(e)}")
            return {'error': str(e)}
    
    def calculate_carbon_footprint_kg(self, qr_code: str) -> Dict:
        """
        Calculate total carbon footprint in kg CO2 for a clothing item.
        
        Args:
            qr_code: QR code of the clothing item
            
        Returns:
            Dict with carbon footprint data:
            {
                'total_kg_co2': float,
                'unit': str,
                'breakdown': [list of material contributions],
                'item_weight_grams': int
            }
        """
        try:
            # Get clothing item details
            item = self.db.get_clothing_item(qr_code)
            if not item:
                return {'error': f'Item with QR code {qr_code} not found'}
            
            # Get material composition
            materials = self.db.get_material_composition(qr_code)
            if not materials:
                return {'error': f'No material composition found for {qr_code}'}
            
            total_carbon_kg = 0.0
            breakdown = []
            
            for material in materials:
                # Get carbon footprint impact for this material
                impact_data = self.db.get_environmental_impact(
                    material['material_name'], 
                    'carbon_footprint'
                )
                
                if impact_data:
                    # Calculate: impact_per_kg * material_percentage * item_weight_kg
                    material_carbon = (
                        impact_data['impact_value'] *  # kg CO2/kg
                        (material['percentage'] / 100) *  # percentage as decimal
                        (item['weight_grams'] / 1000)  # convert grams to kg
                    )
                    
                    total_carbon_kg += material_carbon
                    
                    breakdown.append({
                        'material': material['material_name'],
                        'percentage': material['percentage'],
                        'carbon_kg_co2': round(material_carbon, 3),
                        'impact_per_kg': impact_data['impact_value']
                    })
                else:
                    logger.warning(f"No carbon footprint data for material: {material['material_name']}")
                    breakdown.append({
                        'material': material['material_name'],
                        'percentage': material['percentage'],
                        'carbon_kg_co2': 0.0,
                        'impact_per_kg': 0.0,
                        'note': 'No impact data available'
                    })
            
            return {
                'total_kg_co2': round(total_carbon_kg, 3),
                'unit': 'kg CO2',
                'breakdown': breakdown,
                'item_weight_grams': item['weight_grams'],
                'item_name': item['item_name']
            }
            
        except Exception as e:
            logger.error(f"Error calculating carbon footprint for {qr_code}: {str(e)}")
            return {'error': str(e)}
    
    def calculate_energy_usage_mj(self, qr_code: str) -> Dict:
        """
        Calculate total energy usage in MJ for a clothing item.
        
        Args:
            qr_code: QR code of the clothing item
            
        Returns:
            Dict with energy usage data:
            {
                'total_mj': float,
                'unit': str,
                'breakdown': [list of material contributions],
                'item_weight_grams': int
            }
        """
        try:
            # Get clothing item details
            item = self.db.get_clothing_item(qr_code)
            if not item:
                return {'error': f'Item with QR code {qr_code} not found'}
            
            # Get material composition
            materials = self.db.get_material_composition(qr_code)
            if not materials:
                return {'error': f'No material composition found for {qr_code}'}
            
            total_energy_mj = 0.0
            breakdown = []
            
            for material in materials:
                # Get energy usage impact for this material
                impact_data = self.db.get_environmental_impact(
                    material['material_name'], 
                    'energy_usage'
                )
                
                if impact_data:
                    # Calculate: impact_per_kg * material_percentage * item_weight_kg
                    material_energy = (
                        impact_data['impact_value'] *  # MJ/kg
                        (material['percentage'] / 100) *  # percentage as decimal
                        (item['weight_grams'] / 1000)  # convert grams to kg
                    )
                    
                    total_energy_mj += material_energy
                    
                    breakdown.append({
                        'material': material['material_name'],
                        'percentage': material['percentage'],
                        'energy_mj': round(material_energy, 2),
                        'impact_per_kg': impact_data['impact_value']
                    })
                else:
                    logger.warning(f"No energy usage data for material: {material['material_name']}")
                    breakdown.append({
                        'material': material['material_name'],
                        'percentage': material['percentage'],
                        'energy_mj': 0.0,
                        'impact_per_kg': 0.0,
                        'note': 'No impact data available'
                    })
            
            return {
                'total_mj': round(total_energy_mj, 2),
                'unit': 'MJ',
                'breakdown': breakdown,
                'item_weight_grams': item['weight_grams'],
                'item_name': item['item_name']
            }
            
        except Exception as e:
            logger.error(f"Error calculating energy usage for {qr_code}: {str(e)}")
            return {'error': str(e)}
    
    def calculate_all_impacts(self, qr_code: str) -> Dict:
        """
        Calculate all environmental impacts for a clothing item.
        
        Args:
            qr_code: QR code of the clothing item
            
        Returns:
            Dict with all impact data:
            {
                'item_info': {...},
                'water_usage': {...},
                'carbon_footprint': {...},
                'energy_usage': {...}
            }
        """
        try:
            item = self.db.get_clothing_item(qr_code)
            if not item:
                return {'error': f'Item with QR code {qr_code} not found'}
            
            water_data = self.calculate_water_usage_liters(qr_code)
            carbon_data = self.calculate_carbon_footprint_kg(qr_code)
            energy_data = self.calculate_energy_usage_mj(qr_code)
            
            # Check for errors in individual calculations
            if 'error' in water_data or 'error' in carbon_data or 'error' in energy_data:
                errors = []
                if 'error' in water_data: errors.append(f"Water: {water_data['error']}")
                if 'error' in carbon_data: errors.append(f"Carbon: {carbon_data['error']}")
                if 'error' in energy_data: errors.append(f"Energy: {energy_data['error']}")
                return {'error': '; '.join(errors)}
            
            return {
                'item_info': {
                    'qr_code': qr_code,
                    'name': item['item_name'],
                    'brand': item.get('brand'),
                    'category': item.get('category'),
                    'weight_grams': item['weight_grams']
                },
                'water_usage': water_data,
                'carbon_footprint': carbon_data,
                'energy_usage': energy_data,
                'summary': {
                    'water_liters': water_data['total_liters'],
                    'carbon_kg_co2': carbon_data['total_kg_co2'],
                    'energy_mj': energy_data['total_mj']
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating all impacts for {qr_code}: {str(e)}")
            return {'error': str(e)}
    
    def calculate_cart_impacts(self, cart_items: List[Dict]) -> Dict:
        """
        Calculate total environmental impacts for multiple clothing items (cart).
        
        Args:
            cart_items: List of cart items, each containing 'qr_code'
            
        Returns:
            Dict with total impacts and breakdown:
            {
                'totals': {
                    'water_liters': float,
                    'carbon_kg_co2': float,
                    'energy_mj': float
                },
                'items': [list of individual item impacts],
                'item_count': int
            }
        """
        try:
            if not cart_items:
                return {'error': 'No items in cart'}
            
            total_water = 0.0
            total_carbon = 0.0
            total_energy = 0.0
            item_impacts = []
            
            for cart_item in cart_items:
                qr_code = cart_item.get('qr_code')
                if not qr_code:
                    logger.warning("Cart item missing QR code")
                    continue
                
                # Calculate impacts for this item
                impacts = self.calculate_all_impacts(qr_code)
                
                if 'error' not in impacts:
                    # Add to totals
                    total_water += impacts['water_usage']['total_liters']
                    total_carbon += impacts['carbon_footprint']['total_kg_co2']
                    total_energy += impacts['energy_usage']['total_mj']
                    
                    # Add to items list
                    item_impacts.append({
                        'qr_code': qr_code,
                        'name': impacts['item_info']['name'],
                        'water_liters': impacts['water_usage']['total_liters'],
                        'carbon_kg_co2': impacts['carbon_footprint']['total_kg_co2'],
                        'energy_mj': impacts['energy_usage']['total_mj']
                    })
                else:
                    logger.error(f"Error calculating impacts for {qr_code}: {impacts['error']}")
                    item_impacts.append({
                        'qr_code': qr_code,
                        'name': cart_item.get('name', 'Unknown'),
                        'error': impacts['error']
                    })
            
            return {
                'totals': {
                    'water_liters': round(total_water, 2),
                    'carbon_kg_co2': round(total_carbon, 3),
                    'energy_mj': round(total_energy, 2)
                },
                'items': item_impacts,
                'item_count': len(cart_items),
                'valid_items': len([item for item in item_impacts if 'error' not in item])
            }
            
        except Exception as e:
            logger.error(f"Error calculating cart impacts: {str(e)}")
            return {'error': str(e)}




# ============================================================================
# ESP32 INTEGRATION HELPER
# ============================================================================

def prepare_esp32_data(db_connection, cart_items: List[Dict]) -> Dict:
    """
    Prepare environmental data formatted for ESP32 transmission.
    
    Args:
        db_connection: Database connection
        cart_items: List of cart items
        
    Returns:
        Dict formatted for ESP32DataSender:
        {
            'water_usage': float,
            'carbon_footprint': float,
            'energy_usage': float,
            'item_count': int,
            'items': [list of item details]
        }
    """
    calculator = EnvironmentalCalculator(db_connection)
    cart_impacts = calculator.calculate_cart_impacts(cart_items)
    
    if 'error' in cart_impacts:
        logger.error(f"Error preparing ESP32 data: {cart_impacts['error']}")
        return {
            'water_usage': 0.0,
            'carbon_footprint': 0.0,
            'energy_usage': 0.0,
            'item_count': 0,
            'items': [],
            'error': cart_impacts['error']
        }
    
    # Format for ESP32
    esp32_data = {
        'water_usage': cart_impacts['totals']['water_liters'],
        'carbon_footprint': cart_impacts['totals']['carbon_kg_co2'],
        'energy_usage': cart_impacts['totals']['energy_mj'],
        'item_count': cart_impacts['valid_items'],
        'items': []
    }
    
    # Add individual item details
    for item in cart_impacts['items']:
        if 'error' not in item:
            esp32_data['items'].append({
                'name': item['name'],
                'water_usage': item['water_liters'],
                'carbon_footprint': item['carbon_kg_co2'],
                'energy_usage': item['energy_mj']
            })
    
    return esp32_data


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example usage (requires database to be set up)
    from database import FashionEnvironmentDB  # Assuming your database file is named database.py
    
    # Initialize database
    db = FashionEnvironmentDB()
    calculator = EnvironmentalCalculator(db)
    
    # Test with sample data
    test_qr = "SHIRT001"
    
    print(f"Testing calculations for QR code: {test_qr}")
    print("=" * 50)
    
    # Individual calculations
    water_result = calculator.calculate_water_usage_liters(test_qr)
    carbon_result = calculator.calculate_carbon_footprint_kg(test_qr)
    energy_result = calculator.calculate_energy_usage_mj(test_qr)
    
    if 'error' not in water_result:
        print(f"Water Usage: {water_result['total_liters']} L")
        for item in water_result['breakdown']:
            print(f"  - {item['material']}: {item['water_liters']} L ({item['percentage']}%)")
    
    if 'error' not in carbon_result:
        print(f"\nCarbon Footprint: {carbon_result['total_kg_co2']} kg CO2")
        for item in carbon_result['breakdown']:
            print(f"  - {item['material']}: {item['carbon_kg_co2']} kg CO2 ({item['percentage']}%)")
    
    if 'error' not in energy_result:
        print(f"\nEnergy Usage: {energy_result['total_mj']} MJ")
        for item in energy_result['breakdown']:
            print(f"  - {item['material']}: {item['energy_mj']} MJ ({item['percentage']}%)")
    
    # Test cart calculation
    print("\n" + "=" * 50)
    print("Testing cart calculations:")
    
    test_cart = [
        {'qr_code': 'SHIRT001', 'name': 'Cotton T-Shirt'},
        {'qr_code': 'JEANS001', 'name': 'Denim Jeans'}
    ]
    
    cart_result = calculator.calculate_cart_impacts(test_cart)
    if 'error' not in cart_result:
        totals = cart_result['totals']
        print(f"Cart Totals:")
        print(f"  Water: {totals['water_liters']} L")
        print(f"  Carbon: {totals['carbon_kg_co2']} kg CO2")
        print(f"  Energy: {totals['energy_mj']} MJ")
    
    db.close()