# calculations.py - Sustainability scoring calculations
"""
Comprehensive sustainability calculations for fashion environmental impact analysis.
Contains dual scoring system (Initial Cost vs Lasting Cost) and enhanced scoring.
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


# ============================================================================
# CONFIGURATION CLASSES
# ============================================================================

@dataclass
class DualSustainabilityConfig:
    """Configuration for dual sustainability scoring: Initial Cost vs Lasting Cost"""
    
    # INITIAL COST - Production impact weights (water, energy, CO2)
    initial_cost_weights = {
        'water_usage': 0.40,        # 40% - Water scarcity is critical
        'carbon_footprint': 0.35,   # 35% - Climate impact from production
        'energy_usage': 0.25        # 25% - Energy for manufacturing
    }
    
    # LASTING COST - Lifecycle impact weights
    lasting_cost_weights = {
        'durability_factor': 0.40,      # 40% - How long will it last?
        'end_of_life_impact': 0.35,     # 35% - Biodegradation vs pollution
        'microplastic_pollution': 0.15, # 15% - Ongoing pollution during use
        'replacement_frequency': 0.10   # 10% - How often needs replacing
    }
    
    # Material durability scores (0-100, higher = more durable)
    material_durability_scores = {
        # Natural fibers - excellent durability
        'wool': 90,           # Can last decades with care
        'cashmere': 85,       # High quality but delicate
        'linen': 88,          # Gets better with age
        'hemp': 92,           # Extremely durable
        'silk': 80,           # Delicate but can last long
        'organic cotton': 75,  # Better than conventional
        'conventional cotton': 65,  # Moderate durability
        
        # Synthetic fibers - varies widely
        'nylon': 70,          # Actually quite durable
        'polyester': 45,      # Fast fashion quality, pills
        'recycled polyester': 50,  # Slightly better
        'acrylic': 25,        # Very poor, pills badly
        'viscose': 35,        # Stretches out quickly
        'tencel': 70,         # Better synthetic alternative
        'elastane': 20,       # Loses stretch very quickly
        'spandex': 20         # Degrades rapidly
    }
    
    # End-of-life impact scores (0-100, higher = better for environment)
    end_of_life_scores = {
        # Natural materials - biodegradable
        'wool': 95,            # Biodegrades in 1-5 years
        'organic cotton': 90,   # Biodegrades in months
        'conventional cotton': 80,  # Chemicals slow degradation
        'linen': 95,           # Completely natural
        'hemp': 95,            # Excellent biodegradation
        'silk': 90,            # Natural protein fiber
        'cashmere': 95,        # Natural animal fiber
        
        # Semi-natural/processed
        'tencel': 70,          # Processed but biodegradable
        'viscose': 55,         # Heavily processed cellulose
        
        # Synthetic materials - environmental disaster
        'polyester': 5,        # 200+ years to degrade
        'recycled polyester': 8,   # Still plastic
        'nylon': 3,            # 30-40 years, toxic breakdown
        'acrylic': 2,          # Worst environmental impact
        'elastane': 2,         # Plastic pollution
        'spandex': 2           # Same as elastane
    }
    
    # Microplastic pollution scores (0-100, higher = less pollution)
    microplastic_scores = {
        # Natural materials - no microplastic pollution
        'wool': 100,
        'cotton': 100,
        'organic cotton': 100,
        'conventional cotton': 100,
        'linen': 100,
        'hemp': 100,
        'silk': 100,
        'cashmere': 100,
        
        # Semi-natural
        'tencel': 95,          # Minimal synthetic content
        'viscose': 85,         # Some chemical processing
        
        # Synthetic materials - major microplastic polluters
        'polyester': 15,       # Heavy shedding in wash
        'recycled polyester': 20,  # Still sheds plastic
        'acrylic': 5,          # Worst microplastic shedder
        'nylon': 25,           # Moderate shedding
        'elastane': 20,        # Sheds during washing
        'spandex': 20          # Same as elastane
    }
    
    # Category multipliers for durability expectations
    category_durability_expectations = {
        'outerwear': 1.3,      # Expected to last much longer
        'coat': 1.3,
        'jacket': 1.2,
        'jeans': 1.2,          # Durable category
        'denim': 1.2,
        'knitwear': 1.1,       # Often investment pieces
        'sweater': 1.1,
        't-shirt': 0.9,        # Often replaced frequently
        'underwear': 0.7,      # Hygiene = frequent replacement
        'activewear': 0.8,     # High wear, sweat damage
        'socks': 0.6,          # Wear out quickly
        'dress': 1.0,          # Baseline
        'shirt': 1.0
    }
    
    # Brand quality multipliers (if you want to add brand data)
    brand_quality_multipliers = {
        # Premium brands (last longer)
        'patagonia': 1.2,
        'eileen fisher': 1.15,
        'everlane': 1.1,
        
        # Fast fashion (shorter lifespan)
        'shein': 0.7,
        'fast fashion': 0.75,
        'h&m': 0.8,
        'zara': 0.85,
        
        # Default for unknown brands
        'unknown': 1.0
    }
    
    def get_weight_durability_factor(self, weight_grams):
        """Heavier items often indicate better construction"""
        if weight_grams > 500:     # Heavy items (coats, etc.)
            return 1.15
        elif weight_grams > 300:   # Medium-heavy
            return 1.05
        elif weight_grams < 80:    # Very light (often cheap)
            return 0.9
        else:
            return 1.0


@dataclass
class SustainabilityConfig:
    """Configuration for enhanced sustainability scoring"""
    
    # Category weights for environmental impact
    category_weights = {
        'water_usage': 0.35,       # 35% - Water scarcity critical
        'carbon_footprint': 0.40,  # 40% - Climate change priority
        'energy_usage': 0.25       # 25% - Energy consumption
    }
    
    # Material sustainability bonuses (positive values)
    material_sustainability_bonus = {
        'organic cotton': 15,      # Sustainable farming
        'hemp': 20,               # Very sustainable crop
        'linen': 18,              # Flax is sustainable
        'tencel': 12,             # Made from sustainable wood
        'wool': 10,               # Natural, biodegradable
        'silk': 8,                # Natural protein fiber
        'recycled polyester': 5   # Better than virgin polyester
    }
    
    # Material sustainability penalties (negative values)
    material_sustainability_penalty = {
        'conventional cotton': -5,  # High water/pesticide use
        'acrylic': -15,            # Worst synthetic fiber
        'nylon': -10,              # High energy production
        'polyester': -8,           # Petroleum-based
        'elastane': -12,           # Very difficult to recycle
        'spandex': -12             # Same as elastane
    }
    
    # Category multipliers based on clothing type
    category_multipliers = {
        'outerwear': 1.2,          # Expected to last longer
        'coat': 1.2,
        'jacket': 1.15,
        'jeans': 1.15,
        'knitwear': 1.1,
        'sweater': 1.1,
        'dress': 1.0,              # Baseline
        'shirt': 1.0,
        't-shirt': 0.95,           # Often replaced more frequently
        'underwear': 0.8,          # Hygiene replacement cycle
        'activewear': 0.9,         # High wear and tear
        'socks': 0.7               # Frequent replacement needed
    }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def normalize(value: float, best: float, worst: float) -> float:
    """
    Normalize a value between best and worst on a 0-1 scale.
    
    Args:
        value: The value to normalize
        best: The best possible value (lowest impact)
        worst: The worst possible value (highest impact)
    
    Returns:
        Normalized value between 0 and 1 (1 = best, 0 = worst)
    """
    if worst == best:
        return 1.0
    return max(0, min(1, (worst - value) / (worst - best)))


def calculate_tube_scale(water_liters: float) -> float:
    """
    Convert water usage to tube scale visualization.
    Scale mapping: 4800L = 400ml, so 1L = 0.0833ml on tube scale
    
    Args:
        water_liters: Water usage in liters
    
    Returns:
        Volume on tube scale in ml
    """
    if water_liters <= 0:
        return 0
    
    tube_volume = water_liters * (400 / 4800)
    return round(tube_volume, 2)


def score_to_grade(score: float) -> str:
    """Convert numeric score to letter grade"""
    if score >= 90: return 'A+'
    elif score >= 85: return 'A'
    elif score >= 80: return 'A-'
    elif score >= 75: return 'B+'
    elif score >= 70: return 'B'
    elif score >= 65: return 'B-'
    elif score >= 60: return 'C+'
    elif score >= 55: return 'C'
    elif score >= 50: return 'C-'
    elif score >= 45: return 'D+'
    elif score >= 40: return 'D'
    else: return 'F'


# ============================================================================
# DUAL SUSTAINABILITY SCORER
# ============================================================================

class DualSustainabilityScorer:
    """
    Main class for dual sustainability scoring.
    Calculates Initial Cost (production impact) vs Lasting Cost (lifecycle impact).
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.config = DualSustainabilityConfig()
        self._dynamic_ranges = None
    
    def get_dual_sustainability_score(self, qr_code: str) -> Dict:
        """Calculate both Initial Cost and Lasting Cost scores"""
        item_row = self.db.get_clothing_item(qr_code)
        if not item_row:
            return None
        
        item = dict(item_row)
        materials = self.db.get_material_composition(qr_code)
        if not materials:
            return {'error': 'No material composition found'}
        
        materials = [dict(mat) for mat in materials]
        
        # Validate material composition
        total_percentage = sum(mat['percentage'] for mat in materials)
        if abs(total_percentage - 100) > 1:
            composition_penalty = min(10, abs(total_percentage - 100))
        else:
            composition_penalty = 0
        
        # Calculate INITIAL COST (Production Impact)
        initial_cost_breakdown = self._calculate_initial_cost(item, materials)
        initial_cost_score = initial_cost_breakdown['overall_score']
        
        # Calculate LASTING COST (Lifecycle Impact)
        lasting_cost_breakdown = self._calculate_lasting_cost(item, materials)
        lasting_cost_score = lasting_cost_breakdown['overall_score']
        
        # Apply composition penalty to both scores
        initial_cost_score = max(0, initial_cost_score - composition_penalty)
        lasting_cost_score = max(0, lasting_cost_score - composition_penalty)
        
        # Calculate Final Sustainability Score (average of both)
        final_score = (initial_cost_score + lasting_cost_score) / 2
        
        # Overall sustainability recommendation
        sustainability_insight = self._generate_sustainability_insight(
            initial_cost_score, lasting_cost_score, materials, item
        )
        
        return {
            'qr_code': qr_code,
            'item_name': item['item_name'],
            
            # Dual scoring
            'initial_cost': {
                'score': round(initial_cost_score, 1),
                'grade': score_to_grade(initial_cost_score),
                'breakdown': initial_cost_breakdown
            },
            'lasting_cost': {
                'score': round(lasting_cost_score, 1),
                'grade': score_to_grade(lasting_cost_score),
                'breakdown': lasting_cost_breakdown
            },
            
            # Final combined score
            'final_sustainability_score': {
                'score': round(final_score, 1),
                'grade': score_to_grade(final_score)
            },
            
            # Overall recommendation
            'sustainability_insight': sustainability_insight,
            'composition_penalty': composition_penalty,
            'weight_grams': item['weight_grams'],
            'materials_count': len(materials)
        }
    
    def _calculate_initial_cost(self, item: Dict, materials: List[Dict]) -> Dict:
        """Calculate Initial Cost - production environmental impact"""
        ranges = self._get_dynamic_ranges()
        
        # Calculate production impacts (water, carbon, energy)
        category_scores = {}
        impact_details = {}
        
        for category in self.config.initial_cost_weights.keys():
            total_impact = 0
            material_impacts = []
            
            for material in materials:
                impact_data = self.db.get_environmental_impact(
                    material['material_name'], category
                )
                if impact_data:
                    impact_data = dict(impact_data)
                    material_impact = (
                        impact_data['impact_value'] * 
                        (material['percentage'] / 100) * 
                        (item['weight_grams'] / 1000)
                    )
                    total_impact += material_impact
                    
                    material_impacts.append({
                        'material': material['material_name'],
                        'percentage': material['percentage'],
                        'impact': material_impact,
                        'unit': impact_data['unit']
                    })
            
            # Normalize score (0-100, higher = better = lower impact)
            if category in ranges:
                min_val, max_val = ranges[category]
                if max_val > min_val:
                    # Lower impact = higher score
                    normalized = max(0, min(1, (max_val - total_impact) / (max_val - min_val)))
                else:
                    normalized = 0.5
            else:
                normalized = 0.5
                
            category_scores[category] = normalized * 100
            impact_details[category] = {
                'raw_impact': total_impact,
                'normalized_score': normalized * 100,
                'materials': material_impacts
            }
        
        # Calculate weighted Initial Cost score
        overall_score = sum(
            category_scores[cat] * weight 
            for cat, weight in self.config.initial_cost_weights.items()
            if cat in category_scores
        )
        
        return {
            'overall_score': overall_score,
            'category_scores': {k: round(v, 1) for k, v in category_scores.items()},
            'impact_details': impact_details,
            'explanation': 'Production environmental cost (water, energy, CO2)'
        }
    
    def _calculate_lasting_cost(self, item: Dict, materials: List[Dict]) -> Dict:
        """Calculate Lasting Cost - lifecycle environmental impact"""
        
        # 1. Durability Factor (how long will it last?)
        durability_score = self._calculate_durability_score(item, materials)
        
        # 2. End-of-life Impact (biodegradation vs pollution)
        end_of_life_score = self._calculate_weighted_material_score(
            materials, self.config.end_of_life_scores
        )
        
        # 3. Microplastic Pollution (ongoing pollution during use)
        microplastic_score = self._calculate_weighted_material_score(
            materials, self.config.microplastic_scores
        )
        
        # 4. Replacement Frequency (inverse of durability)
        replacement_score = durability_score  # Same as durability but conceptually different
        
        # Calculate weighted Lasting Cost score
        component_scores = {
            'durability_factor': durability_score,
            'end_of_life_impact': end_of_life_score,
            'microplastic_pollution': microplastic_score,
            'replacement_frequency': replacement_score
        }
        
        overall_score = sum(
            component_scores[component] * weight 
            for component, weight in self.config.lasting_cost_weights.items()
        )
        
        return {
            'overall_score': overall_score,
            'component_scores': {k: round(v, 1) for k, v in component_scores.items()},
            'explanation': 'Lifetime environmental cost (durability, pollution, disposal)'
        }
    
    def _calculate_durability_score(self, item: Dict, materials: List[Dict]) -> float:
        """Calculate how durable/long-lasting the item will be"""
        # Base durability from materials
        weighted_durability = self._calculate_weighted_material_score(
            materials, self.config.material_durability_scores
        )
        
        # Apply category expectations
        category = item.get('category', '').lower()
        category_multiplier = self.config.category_durability_expectations.get(category, 1.0)
        
        # Apply weight-based durability factor
        weight_factor = self.config.get_weight_durability_factor(item['weight_grams'])
        
        # Apply brand quality if available
        brand = item.get('brand', '').lower()
        brand_multiplier = self.config.brand_quality_multipliers.get(brand, 1.0)
        
        # Final durability score
        final_score = weighted_durability * category_multiplier * weight_factor * brand_multiplier
        
        return min(100, final_score)  # Cap at 100
    
    def _calculate_weighted_material_score(self, materials: List[Dict], score_dict: Dict) -> float:
        """Calculate weighted average score based on material composition"""
        weighted_score = 0
        
        for material in materials:
            material_name = material['material_name'].lower()
            material_score = score_dict.get(material_name, 50)  # Default neutral score
            weight_percentage = material['percentage'] / 100
            weighted_score += material_score * weight_percentage
        
        return weighted_score
    
    def _generate_sustainability_insight(self, initial_cost: float, lasting_cost: float, 
                                       materials: List[Dict], item: Dict) -> Dict:
        """Generate insight comparing Initial vs Lasting costs"""
        
        # Determine dominant material
        dominant_material = max(materials, key=lambda m: m['percentage'])
        material_name = dominant_material['material_name'].lower()
        
        # Generate recommendation based on score comparison
        if initial_cost >= 70 and lasting_cost >= 70:
            recommendation = "🌟 Excellent Choice"
            explanation = "Low production impact AND great longevity. This is a truly sustainable option."
            
        elif initial_cost < 40 and lasting_cost >= 70:
            recommendation = "🔄 Trade-off Worth Making"
            explanation = f"Higher production impact, but {material_name} will last much longer and biodegrade naturally. The long-term benefits outweigh the initial cost."
            
        elif initial_cost >= 70 and lasting_cost < 40:
            recommendation = "⚠️ Short-term Thinking"
            explanation = "Low production impact but poor longevity. You'll likely need to replace this frequently, increasing overall environmental cost."
            
        elif initial_cost < 40 and lasting_cost < 40:
            recommendation = "🚨 Avoid if Possible"
            explanation = "High production impact AND poor longevity. This represents the worst of both worlds environmentally."
            
        else:
            recommendation = "⚖️ Balanced Choice"
            explanation = "Moderate impact in both production and longevity. Consider your specific needs and usage patterns."
        
        # Add specific material insights
        material_insights = []
        if 'wool' in material_name or 'cashmere' in material_name:
            material_insights.append("Natural fibers like wool use more water initially but last decades and biodegrade completely")
        elif 'polyester' in material_name or 'acrylic' in material_name:
            material_insights.append("Synthetic materials are cheaper to produce but create microplastic pollution and never biodegrade")
        elif 'cotton' in material_name:
            material_insights.append("Cotton is biodegradable but very water-intensive to produce")
        
        return {
            'recommendation': recommendation,
            'explanation': explanation,
            'material_insights': material_insights,
            'score_comparison': {
                'initial_higher': initial_cost > lasting_cost,
                'difference': abs(initial_cost - lasting_cost)
            }
        }
    
    def _get_dynamic_ranges(self) -> Dict:
        """Get production impact ranges for normalization"""
        if self._dynamic_ranges:
            return self._dynamic_ranges
        
        # Use hardcoded ranges for now - could be made dynamic from database
        self._dynamic_ranges = {
            'water_usage': (5.91996, 6000),
            'carbon_footprint': (0.9, 10.4),
            'energy_usage': (1.09323, 138)
        }
        return self._dynamic_ranges
    
    def calculate_cart_dual_score(self, cart_items: List[Dict]) -> Dict:
        """Calculate dual scores for entire cart"""
        if not cart_items:
            return {'error': 'Empty cart'}
        
        item_scores = []
        total_weight = 0
        initial_cost_total = 0
        lasting_cost_total = 0
        
        for cart_item in cart_items:
            qr_code = cart_item['qr_code']
            detailed_score = self.get_dual_sustainability_score(qr_code)
            
            if detailed_score and 'error' not in detailed_score:
                item_scores.append(detailed_score)
                weight = detailed_score['weight_grams']
                total_weight += weight
                
                # Weight-adjusted contributions
                initial_cost_total += detailed_score['initial_cost']['score'] * weight
                lasting_cost_total += detailed_score['lasting_cost']['score'] * weight
        
        if not item_scores:
            return {'error': 'No valid items scored'}
        
        # Calculate weighted averages
        avg_initial_cost = initial_cost_total / total_weight if total_weight > 0 else 0
        avg_lasting_cost = lasting_cost_total / total_weight if total_weight > 0 else 0
        final_cart_score = (avg_initial_cost + avg_lasting_cost) / 2
        
        # Generate cart-level insights
        cart_insights = self._generate_cart_insights(item_scores, avg_initial_cost, avg_lasting_cost)
        
        return {
            'cart_initial_cost': {
                'score': round(avg_initial_cost, 1),
                'grade': score_to_grade(avg_initial_cost)
            },
            'cart_lasting_cost': {
                'score': round(avg_lasting_cost, 1),
                'grade': score_to_grade(avg_lasting_cost)
            },
            'cart_final_score': {
                'score': round(final_cart_score, 1),
                'grade': score_to_grade(final_cart_score)
            },
            'item_scores': item_scores,
            'total_items': len(item_scores),
            'total_weight_grams': total_weight,
            'cart_insights': cart_insights
        }
    
    def _generate_cart_insights(self, item_scores: List[Dict], avg_initial: float, avg_lasting: float) -> List[str]:
        """Generate insights for the entire cart"""
        insights = []
        
        if avg_initial >= 70 and avg_lasting >= 70:
            insights.append("🌟 Excellent cart! Low production impact with great longevity")
        elif avg_initial < 40 and avg_lasting >= 70:
            insights.append("🔄 Investment mindset: Higher initial cost, but items will last much longer")
        elif avg_initial >= 70 and avg_lasting < 40:
            insights.append("⚠️ Fast fashion pattern: Low production cost but frequent replacement needed")
        
        # Material-based insights (simplified logic)
        natural_materials = sum(1 for item in item_scores if avg_lasting >= 60)
        synthetic_materials = len(item_scores) - natural_materials
        
        if natural_materials > synthetic_materials:
            insights.append("🌱 Your cart favors natural, biodegradable materials")
        elif synthetic_materials > natural_materials:
            insights.append("🧪 Your cart contains mostly synthetic materials - consider natural alternatives")
        
        return insights


# ============================================================================
# ENHANCED SUSTAINABILITY SCORER
# ============================================================================

class EnhancedSustainabilityScorer:
    """
    Enhanced sustainability scoring system with dynamic range calculation
    and comprehensive material analysis.
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.config = SustainabilityConfig()
        self._dynamic_ranges = None
        
    def calculate_dynamic_ranges(self) -> Dict[str, Tuple[float, float]]:
        """Calculate min/max ranges from actual database data"""
        if self._dynamic_ranges:
            return self._dynamic_ranges
            
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        ranges = {}
        categories = ['water_usage', 'carbon_footprint', 'energy_usage']
        
        for category in categories:
            # Get all impact values for this category, weighted by typical usage
            cursor.execute('''
            SELECT ei.impact_value, 
                   AVG(cmc.percentage) as avg_percentage,
                   AVG(ci.weight_grams) as avg_weight
            FROM environmental_impacts ei
            JOIN materials m ON ei.material_id = m.material_id
            JOIN clothing_material_composition cmc ON m.material_id = cmc.material_id
            JOIN clothing_items ci ON cmc.qr_code = ci.qr_code
            WHERE ei.impact_category = ?
            GROUP BY ei.impact_value
            ''', (category,))
            
            results = cursor.fetchall()
            
            if results:
                # Calculate realistic impact values
                calculated_impacts = []
                for row in results:
                    row_dict = dict(row)
                    impact_value = row_dict['impact_value']
                    avg_percentage = row_dict['avg_percentage'] or 50  # Default if null
                    avg_weight = row_dict['avg_weight'] or 200  # Default if null
                    
                    calculated_impact = impact_value * (avg_percentage/100) * (avg_weight/1000)
                    calculated_impacts.append(calculated_impact)
                
                if calculated_impacts:
                    ranges[category] = (min(calculated_impacts), max(calculated_impacts))
                else:
                    # Fallback to hardcoded values
                    fallback_ranges = {
                        'water_usage': (5.91996, 6000),
                        'carbon_footprint': (0.9, 10.4),
                        'energy_usage': (1.09323, 138)
                    }
                    ranges[category] = fallback_ranges.get(category, (0, 100))
        
        conn.close()
        self._dynamic_ranges = ranges
        return ranges
    
    def get_item_detailed_score(self, qr_code: str) -> Dict:
        """Calculate detailed sustainability score with breakdown"""
        item_row = self.db.get_clothing_item(qr_code)
        if not item_row:
            return None
        
        item = dict(item_row)
        materials = self.db.get_material_composition(qr_code)
        if not materials:
            return {'error': 'No material composition found'}
        
        materials = [dict(mat) for mat in materials]
        
        # Validate material composition totals 100%
        total_percentage = sum(mat['percentage'] for mat in materials)
        if abs(total_percentage - 100) > 1:
            composition_penalty = min(20, abs(total_percentage - 100) * 2)
        else:
            composition_penalty = 0
        
        ranges = self.calculate_dynamic_ranges()
        
        # Calculate base impact scores
        category_scores = {}
        impact_breakdown = {}
        
        for category in self.config.category_weights.keys():
            total_impact = 0
            material_details = []
            
            for material in materials:
                impact_data = self.db.get_environmental_impact(
                    material['material_name'], category
                )
                if impact_data:
                    impact_data = dict(impact_data) if hasattr(impact_data, 'keys') else impact_data
                    
                    material_impact = (
                        impact_data['impact_value'] * 
                        (material['percentage'] / 100) * 
                        (item['weight_grams'] / 1000)
                    )
                    total_impact += material_impact
                    
                    material_details.append({
                        'material': material['material_name'],
                        'percentage': material['percentage'],
                        'impact': material_impact,
                        'unit': impact_data['unit']
                    })
            
            # Normalize score (0-100, where 100 is best)
            if category in ranges:
                min_val, max_val = ranges[category]
                if max_val > min_val:
                    normalized = max(0, min(1, (max_val - total_impact) / (max_val - min_val)))
                else:
                    normalized = 1.0
            else:
                normalized = 0.5  # Default if no range data
                
            category_scores[category] = normalized * 100
            impact_breakdown[category] = {
                'raw_impact': total_impact,
                'normalized_score': normalized * 100,
                'materials': material_details
            }
        
        # Apply weighted average
        weighted_score = sum(
            category_scores[cat] * weight 
            for cat, weight in self.config.category_weights.items()
            if cat in category_scores
        )
        
        # Apply material sustainability bonuses/penalties
        material_bonus = 0
        for material in materials:
            material_name = material['material_name'].lower()
            percentage_weight = material['percentage'] / 100
            
            if material_name in self.config.material_sustainability_bonus:
                material_bonus += (
                    self.config.material_sustainability_bonus[material_name] * 
                    percentage_weight
                )
            elif material_name in self.config.material_sustainability_penalty:
                material_bonus += (
                    self.config.material_sustainability_penalty[material_name] * 
                    percentage_weight
                )
        
        # Apply category multiplier
        category = item.get('category', '').lower()
        category_multiplier = self.config.category_multipliers.get(category, 1.0)
        
        # Calculate final score
        final_score = weighted_score + material_bonus - composition_penalty
        final_score = final_score / category_multiplier  # Lower multiplier = worse score
        final_score = max(0, min(100, final_score))  # Clamp to 0-100
        
        return {
            'qr_code': qr_code,
            'item_name': item['item_name'],
            'final_score': round(final_score, 1),
            'category_scores': {k: round(v, 1) for k, v in category_scores.items()},
            'impact_breakdown': impact_breakdown,
            'adjustments': {
                'material_bonus': round(material_bonus, 1),
                'composition_penalty': round(composition_penalty, 1),
                'category_multiplier': category_multiplier
            },
            'grade': score_to_grade(final_score),
            'weight_grams': item['weight_grams'],
            'materials_count': len(materials)
        }
    
    def calculate_cart_score(self, cart_items: List[Dict]) -> Dict:
        """Calculate comprehensive cart sustainability score"""
        if not cart_items:
            return {'error': 'Empty cart'}
        
        item_scores = []
        total_weight = 0
        category_totals = {cat: 0 for cat in self.config.category_weights.keys()}
        
        for cart_item in cart_items:
            qr_code = cart_item['qr_code']
            detailed_score = self.get_item_detailed_score(qr_code)
            
            if detailed_score and 'error' not in detailed_score:
                item_scores.append(detailed_score)
                weight = detailed_score['weight_grams']
                total_weight += weight
                
                # Weight-adjusted category contributions
                for category, score in detailed_score['category_scores'].items():
                    category_totals[category] += score * weight
        
        if not item_scores:
            return {'error': 'No valid items scored'}
        
        # Calculate weighted averages
        avg_category_scores = {
            cat: total / total_weight if total_weight > 0 else 0
            for cat, total in category_totals.items()
        }
        
        # Overall cart score (weighted average of category scores)
        cart_score = sum(
            avg_category_scores[cat] * weight 
            for cat, weight in self.config.category_weights.items()
        )
        
        # Diversity bonus (having fewer, higher-quality items vs many low-quality)
        diversity_factor = 1.0
        if len(item_scores) <= 3:  # Encourage capsule wardrobes
            diversity_factor = 1.05
        
        final_cart_score = min(100, cart_score * diversity_factor)
        
        return {
            'cart_score': round(final_cart_score, 1),
            'grade': score_to_grade(final_cart_score),
            'category_breakdown': {k: round(v, 1) for k, v in avg_category_scores.items()},
            'item_scores': item_scores,
            'total_items': len(item_scores),
            'total_weight_grams': total_weight,
            'average_item_score': round(sum(item['final_score'] for item in item_scores) / len(item_scores), 1),
            'diversity_factor': diversity_factor,
            'recommendations': self._generate_recommendations(item_scores, avg_category_scores)
        }
    
    def _generate_recommendations(self, item_scores: List[Dict], category_scores: Dict) -> List[str]:
        """Generate sustainability improvement recommendations"""
        recommendations = []
        
        # Find worst-performing category
        worst_category = min(category_scores.keys(), key=lambda k: category_scores[k])
        worst_score = category_scores[worst_category]
        
        if worst_score < 60:
            category_names = {
                'water_usage': 'water consumption',
                'carbon_footprint': 'carbon emissions', 
                'energy_usage': 'energy consumption'
            }
            recommendations.append(
                f"Consider replacing items with high {category_names.get(worst_category, worst_category)}"
            )
        
        # Find lowest-scoring items
        low_scoring_items = [item for item in item_scores if item['final_score'] < 50]
        if low_scoring_items:
            recommendations.append(
                f"Consider alternatives for: {', '.join(item['item_name'] for item in low_scoring_items[:2])}"
            )
        
        # Material-specific recommendations
        all_materials = []
        for item in item_scores:
            for category_breakdown in item['impact_breakdown'].values():
                all_materials.extend([mat['material'] for mat in category_breakdown['materials']])
        
        if 'conventional cotton' in all_materials:
            recommendations.append("Look for organic cotton alternatives to reduce water usage")
        
        if 'acrylic' in all_materials or 'nylon' in all_materials:
            recommendations.append("Consider natural fiber alternatives to synthetic materials")
        
        return recommendations[:3]  # Limit to top 3 recommendations


# ============================================================================
# BASIC IMPACT CALCULATIONS
# ============================================================================

def calculate_basic_sustainability_score(cart_items: List[Dict], db_connection) -> Dict:
    """
    Calculate basic sustainability score using the original algorithm.
    Used for simple scoring without the advanced dual or enhanced systems.
    """
    if not cart_items:
        return {'error': 'Empty cart'}
    
    # Hardcoded min/max ranges (from original implementation)
    minmax = {
        'water_usage': (5.91996, 6000),
        'carbon_footprint': (0.9, 10.4),
        'energy_usage': (1.09323, 138)
    }
    
    def get_item_score(qr_code):
        impacts = {}
        item = db_connection.get_clothing_item(qr_code)
        if not item:
            return None
        
        materials = db_connection.get_material_composition(qr_code)
        for category in minmax:
            total = 0
            for mat in materials:
                impact_data = db_connection.get_environmental_impact(mat['material_name'], category)
                if impact_data:
                    total += impact_data['impact_value'] * (mat['percentage']/100) * (item['weight_grams']/1000)
            impacts[category] = total
        
        scores = [normalize(impacts[cat], minmax[cat][0], minmax[cat][1]) for cat in minmax]
        return sum(scores) / len(scores) * 100
    
    item_scores = []
    for item in cart_items:
        score = get_item_score(item['qr_code'])
        if score is not None:
            item_scores.append({
                'name': item['name'], 
                'qr_code': item['qr_code'],
                'score': round(score, 1)
            })
    
    if not item_scores:
        return {'error': 'No valid items scored'}
    
    scores = [s['score'] for s in item_scores]
    sustainability_score = round(sum(scores) / len(scores), 1)
    
    return {
        'sustainability_score': sustainability_score,
        'grade': score_to_grade(sustainability_score),
        'item_scores': item_scores,
        'total_items': len(item_scores)
    }


def calculate_environmental_impacts(qr_code: str, db_connection) -> Dict:
    """
    Calculate raw environmental impacts for a single item.
    Returns the basic impact analysis used in the main analyzer.
    """
    try:
        # Get clothing item
        item = db_connection.get_clothing_item(qr_code)
        if not item:
            return {'error': f'No item found with QR code: {qr_code}'}
        
        # Get material composition
        materials = db_connection.get_material_composition(qr_code)
        
        # Calculate environmental impacts
        impact_categories = ["water_usage", "carbon_footprint", "energy_usage"]
        category_names = {
            "water_usage": "💧 Water Usage",
            "carbon_footprint": "🏭 Carbon Footprint", 
            "energy_usage": "⚡ Energy Usage"
        }
        
        results = {
            'item': dict(item),
            'materials': [dict(mat) for mat in materials],
            'impacts': {}
        }
        
        total_impacts = {}
        
        for category in impact_categories:
            category_total = 0
            unit = None
            material_impacts = []
            
            for material in materials:
                impact_data = db_connection.get_environmental_impact(material['material_name'], category)
                if impact_data:
                    # Calculate material impact
                    material_impact = (
                        impact_data['impact_value'] * 
                        (material['percentage'] / 100) * 
                        (item['weight_grams'] / 1000)
                    )
                    category_total += material_impact
                    unit = impact_data['unit']
                    
                    material_impacts.append({
                        'material': material['material_name'].title(),
                        'impact': material_impact,
                        'percentage': material['percentage'],
                        'base_impact': impact_data['impact_value'],
                        'unit': impact_data['unit']
                    })
            
            if unit:
                # Remove /kg from final unit display
                final_unit = unit.replace('/kg', '')
                total_impacts[category] = {
                    'value': category_total, 
                    'unit': final_unit,
                    'name': category_names[category],
                    'materials': material_impacts
                }
        
        results['impacts'] = total_impacts
        
        # Add tube scale calculation for water usage
        water_usage = total_impacts.get('water_usage', {}).get('value', 0)
        results['tube_scale'] = calculate_tube_scale(water_usage)
        
        return results
        
    except Exception as e:
        return {'error': str(e)}