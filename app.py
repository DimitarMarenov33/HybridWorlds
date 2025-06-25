# app.py - Add this file to your existing project
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response, flash
import sqlite3
import os
from datetime import datetime
import traceback
import math
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from esp32_sender import ESP32DataSender
import threading
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Needed for session

esp32_data_store = {
    'environmental_data': None,
    'has_new_data': False,
    'last_updated': None,
    'last_polled': None
}
data_store_lock = threading.Lock()


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
    
    # Weight-based durability bonus
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

class DualSustainabilityScorer:
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
                'grade': self._score_to_grade(initial_cost_score),
                'breakdown': initial_cost_breakdown
            },
            'lasting_cost': {
                'score': round(lasting_cost_score, 1),
                'grade': self._score_to_grade(lasting_cost_score),
                'breakdown': lasting_cost_breakdown
            },
            
            # Final combined score
            'final_sustainability_score': {
                'score': round(final_score, 1),
                'grade': self._score_to_grade(final_score)
            },
            
            # Overall recommendation
            'sustainability_insight': sustainability_insight,
            'composition_penalty': composition_penalty,
            'weight_grams': item['weight_grams'],
            'materials_count': len(materials)
        }
    
    def _calculate_initial_cost(self, item, materials) -> Dict:
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
    
    def _calculate_lasting_cost(self, item, materials) -> Dict:
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
    
    def _calculate_durability_score(self, item, materials) -> float:
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
    
    def _calculate_weighted_material_score(self, materials, score_dict) -> float:
        """Calculate weighted average score based on material composition"""
        weighted_score = 0
        
        for material in materials:
            material_name = material['material_name'].lower()
            material_score = score_dict.get(material_name, 50)  # Default neutral score
            weight_percentage = material['percentage'] / 100
            weighted_score += material_score * weight_percentage
        
        return weighted_score
    
    def _generate_sustainability_insight(self, initial_cost, lasting_cost, materials, item) -> Dict:
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
        
        # Use hardcoded ranges for now
        self._dynamic_ranges = {
            'water_usage': (5.91996, 6000),
            'carbon_footprint': (0.9, 10.4),
            'energy_usage': (1.09323, 138)
        }
        return self._dynamic_ranges
    
    def _score_to_grade(self, score: float) -> str:
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
        # Calculate final average score
        final_cart_score = (avg_initial_cost + avg_lasting_cost) / 2
        # Generate cart-level insights
        cart_insights = self._generate_cart_insights(item_scores, avg_initial_cost, avg_lasting_cost)
        
        return {
            'cart_initial_cost': {
                'score': round(avg_initial_cost, 1),
                'grade': self._score_to_grade(avg_initial_cost)
            },
            'cart_lasting_cost': {
                'score': round(avg_lasting_cost, 1),
                'grade': self._score_to_grade(avg_lasting_cost)
            },
            'cart_final_score': {
                'score': round(final_cart_score, 1),
                'grade': self._score_to_grade(final_cart_score)
            },
            'item_scores': item_scores,
            'total_items': len(item_scores),
            'total_weight_grams': total_weight,
            'cart_insights': cart_insights
        }
    
    def _generate_cart_insights(self, item_scores, avg_initial, avg_lasting) -> List[str]:
        """Generate insights for the entire cart"""
        insights = []
        
        if avg_initial >= 70 and avg_lasting >= 70:
            insights.append("🌟 Excellent cart! Low production impact with great longevity")
        elif avg_initial < 40 and avg_lasting >= 70:
            insights.append("🔄 Investment mindset: Higher initial cost, but items will last much longer")
        elif avg_initial >= 70 and avg_lasting < 40:
            insights.append("⚠️ Fast fashion pattern: Low production cost but frequent replacement needed")
        
        # Material-based insights
        natural_materials = 0
        synthetic_materials = 0
        
        for item in item_scores:
            # This would need to be extracted from the item data
            # For now, simplified logic
            if avg_lasting >= 60:
                natural_materials += 1
            else:
                synthetic_materials += 1
        
        if natural_materials > synthetic_materials:
            insights.append("🌱 Your cart favors natural, biodegradable materials")
        elif synthetic_materials > natural_materials:
            insights.append("🧪 Your cart contains mostly synthetic materials - consider natural alternatives")
        
        return insights

class EnhancedSustainabilityScorer:
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
                    # Convert sqlite3.Row to dict to handle safely
                    row_dict = dict(row)
                    impact_value = row_dict['impact_value']
                    avg_percentage = row_dict['avg_percentage'] or 50  # Default if null
                    avg_weight = row_dict['avg_weight'] or 200  # Default if null
                    
                    calculated_impact = impact_value * (avg_percentage/100) * (avg_weight/1000)
                    calculated_impacts.append(calculated_impact)
                
                if calculated_impacts:
                    ranges[category] = (min(calculated_impacts), max(calculated_impacts))
                else:
                    # Fallback to original hardcoded values
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
        
        # Convert sqlite3.Row to dictionary to use .get() method
        item = dict(item_row)
            
        materials = self.db.get_material_composition(qr_code)
        if not materials:
            return {'error': 'No material composition found'}
        
        # Convert materials to dictionaries too
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
                    # Convert impact_data to dict if it's a Row object
                    if hasattr(impact_data, 'keys'):
                        impact_data = dict(impact_data)
                    
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
            'grade': self._score_to_grade(final_score),
            'weight_grams': item['weight_grams'],
            'materials_count': len(materials)
        }
    
    def _score_to_grade(self, score: float) -> str:
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
            'grade': self._score_to_grade(final_cart_score),
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
    

dual_scorer = None

def initialize_dual_scorer():
    """Initialize the dual sustainability scorer"""
    global dual_scorer
    dual_scorer = DualSustainabilityScorer(db)

# Dual scoring endpoints
@app.route('/api/dual_analyze/<qr_code>')
def dual_analyze_item(qr_code):
    """Analyze item with dual sustainability scoring (Initial vs Lasting Cost)"""
    try:
        if not dual_scorer:
            initialize_dual_scorer()
            
        result = dual_scorer.get_dual_sustainability_score(qr_code)
        if result:
            return jsonify(result)
        else:
            return jsonify({'error': 'Item not found'}), 404
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/dual_cart_summary')
def dual_cart_summary():
    """Calculate dual sustainability scores for entire cart"""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
        
    cart_items = session.get('cart_items', [])
    if not cart_items:
        return jsonify({'error': 'Empty cart'}), 400
        
    try:
        if not dual_scorer:
            initialize_dual_scorer()
            
        result = dual_scorer.calculate_cart_dual_score(cart_items)
        return jsonify(result)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/dual_config')
def get_dual_config():
    """Return dual scoring configuration for transparency"""
    if not dual_scorer:
        initialize_dual_scorer()
        
    return jsonify({
        'initial_cost_weights': dual_scorer.config.initial_cost_weights,
        'lasting_cost_weights': dual_scorer.config.lasting_cost_weights,
        'material_durability_scores': dual_scorer.config.material_durability_scores,
        'end_of_life_scores': dual_scorer.config.end_of_life_scores,
        'explanation': {
            'initial_cost': 'Production environmental impact (water, energy, CO2)',
            'lasting_cost': 'Lifetime environmental impact (durability, pollution, disposal)'
        }
    })

# Debug endpoint for dual scoring
@app.route('/api/debug_dual_scoring')
def debug_dual_scoring():
    """Debug route to test dual scoring system"""
    try:
        username = session.get('username')
        cart_items = session.get('cart_items', [])
        
        debug_info = {
            'username': username,
            'cart_items_count': len(cart_items),
            'cart_items': cart_items
        }
        
        if not username:
            debug_info['error'] = 'No username in session'
            return jsonify(debug_info)
        
        if not cart_items:
            debug_info['error'] = 'No cart items'
            return jsonify(debug_info)
        
        # Test dual scorer initialization
        try:
            if not dual_scorer:
                initialize_dual_scorer()
            debug_info['dual_scorer_created'] = True
        except Exception as e:
            debug_info['dual_scorer_error'] = str(e)
            return jsonify(debug_info)
        
        # Test each cart item
        item_tests = []
        for i, cart_item in enumerate(cart_items):
            qr_code = cart_item.get('qr_code')
            item_test = {
                'index': i,
                'qr_code': qr_code,
                'item_name': cart_item.get('name')
            }
            
            try:
                dual_score = dual_scorer.get_dual_sustainability_score(qr_code)
                if dual_score and 'error' not in dual_score:
                    item_test['dual_scoring_success'] = True
                    item_test['initial_cost'] = dual_score['initial_cost']['score']
                    item_test['lasting_cost'] = dual_score['lasting_cost']['score']
                    item_test['insight'] = dual_score['sustainability_insight']['recommendation']
                else:
                    item_test['dual_scoring_error'] = dual_score.get('error', 'Unknown error')
            except Exception as e:
                item_test['dual_scoring_exception'] = str(e)
                import traceback
                item_test['dual_scoring_traceback'] = traceback.format_exc()
            
            item_tests.append(item_test)
        
        debug_info['item_tests'] = item_tests
        
        # Test cart scoring
        try:
            cart_result = dual_scorer.calculate_cart_dual_score(cart_items)
            debug_info['cart_dual_scoring_success'] = True
            debug_info['cart_result'] = cart_result
        except Exception as e:
            debug_info['cart_dual_scoring_error'] = str(e)
            import traceback
            debug_info['cart_dual_scoring_traceback'] = traceback.format_exc()
        
        return jsonify(debug_info)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': True,
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

# Update the app initialization
def initialize_all_scorers():
    """Initialize all scoring systems"""
    initialize_dual_scorer()
    # Keep your existing scorer if you want both
    # integrate_enhanced_scoring(app, db)
    
# Use your existing database class structure
class FashionEnvironmentDB:
    def __init__(self, db_path="fashion_env.db"):
        self.db_path = db_path
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_clothing_item(self, qr_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clothing_items WHERE qr_code = ?', (qr_code,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def get_material_composition(self, qr_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT m.material_name, cmc.percentage
        FROM clothing_material_composition cmc
        JOIN materials m ON cmc.material_id = m.material_id
        WHERE cmc.qr_code = ?
        ''', (qr_code,))
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_environmental_impact(self, material_name, impact_category):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT ei.impact_value, ei.unit
        FROM environmental_impacts ei
        JOIN materials m ON ei.material_id = m.material_id
        WHERE m.material_name = ? AND ei.impact_category = ?
        ''', (material_name.lower(), impact_category))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def list_all_clothing_items(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clothing_items ORDER BY item_name')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def list_all_materials(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM materials ORDER BY material_name')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def add_clothing_item(self, qr_code, name, weight_grams, brand=None, category=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO clothing_items (qr_code, item_name, brand, category, weight_grams)
            VALUES (?, ?, ?, ?, ?)
            ''', (qr_code, name, brand, category, weight_grams))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def add_material(self, name, density=None, description=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO materials (material_name, density_g_per_cm3, description)
            VALUES (?, ?, ?)
            ''', (name.lower(), density, description))
            conn.commit()
            material_id = cursor.lastrowid
            conn.close()
            return material_id
        except sqlite3.IntegrityError:
            conn.close()
            return None
    
    def add_material_composition(self, qr_code, material_name, percentage):
        """Add material composition for a clothing item"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get material ID
        cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name.lower(),))
        material = cursor.fetchone()
        
        if not material:
            conn.close()
            return False
        
        try:
            cursor.execute('''
            INSERT INTO clothing_material_composition (qr_code, material_id, percentage)
            VALUES (?, ?, ?)
            ''', (qr_code, material['material_id'], percentage))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            conn.close()
            return False
    
    def list_all_materials_with_impact_count(self):
        """Get all materials with their impact data count"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT m.*, 
               COUNT(ei.impact_id) as impact_count
        FROM materials m
        LEFT JOIN environmental_impacts ei ON m.material_id = ei.material_id
        GROUP BY m.material_id, m.material_name, m.density_g_per_cm3, m.description
        ORDER BY m.material_name
        ''')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def list_all_environmental_impacts(self):
        """Get all environmental impacts with material names"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT ei.impact_id, m.material_name, ei.impact_category, 
               ei.impact_value, ei.unit, ei.source
        FROM environmental_impacts ei
        JOIN materials m ON ei.material_id = m.material_id
        ORDER BY m.material_name, ei.impact_category
        ''')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def add_environmental_impact(self, material_name, impact_category, impact_value, unit, source=None):
        """Add environmental impact data for a material"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get material ID
        cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name.lower(),))
        material = cursor.fetchone()
        
        if not material:
            conn.close()
            return False
        
        try:
            cursor.execute('''
            INSERT INTO environmental_impacts (material_id, impact_category, impact_value, unit, source)
            VALUES (?, ?, ?, ?, ?)
            ''', (material['material_id'], impact_category, impact_value, unit, source))
            
            impact_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return impact_id
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def update_environmental_impact(self, impact_id, material_name, impact_category, impact_value, unit, source=None):
        """Update existing environmental impact data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get material ID
        cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name.lower(),))
        material = cursor.fetchone()
        
        if not material:
            conn.close()
            return False
        
        try:
            cursor.execute('''
            UPDATE environmental_impacts 
            SET material_id=?, impact_category=?, impact_value=?, unit=?, source=?
            WHERE impact_id=?
            ''', (material['material_id'], impact_category, impact_value, unit, source, impact_id))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            conn.close()
            return False
    
    def delete_environmental_impact(self, impact_id):
        """Delete environmental impact data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM environmental_impacts WHERE impact_id = ?", (impact_id,))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            conn.close()
            return False
    
    def update_material(self, material_id, name, density=None, description=None):
        """Update existing material"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            UPDATE materials 
            SET material_name=?, density_g_per_cm3=?, description=?
            WHERE material_id=?
            ''', (name.lower(), density, description, material_id))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            conn.close()
            return False
    
    def delete_material(self, material_id):
        """Delete material and associated data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Delete environmental impacts first
            cursor.execute("DELETE FROM environmental_impacts WHERE material_id = ?", (material_id,))
            
            # Delete material compositions
            cursor.execute("DELETE FROM clothing_material_composition WHERE material_id = ?", (material_id,))
            
            # Delete material
            cursor.execute("DELETE FROM materials WHERE material_id = ?", (material_id,))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            conn.close()
            return False
    
    def update_clothing_item(self, qr_code, name, weight_grams, brand=None, category=None):
        """Update existing clothing item"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            UPDATE clothing_items 
            SET item_name=?, brand=?, category=?, weight_grams=?
            WHERE qr_code=?
            ''', (name, brand, category, weight_grams, qr_code))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            conn.close()
            return False
    
    def delete_clothing_item(self, qr_code):
        """Delete clothing item and its material composition"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Delete material composition first (foreign key constraint)
            cursor.execute("DELETE FROM clothing_material_composition WHERE qr_code = ?", (qr_code,))
            
            # Delete clothing item
            cursor.execute("DELETE FROM clothing_items WHERE qr_code = ?", (qr_code,))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            conn.close()
            return False
    
    def clear_material_composition(self, qr_code):
        """Clear all material composition for an item"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM clothing_material_composition WHERE qr_code=?', (qr_code,))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            conn.close()
            return False
    
    def get_database_stats(self):
        """Get overview statistics for the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Get counts
        cursor.execute('SELECT COUNT(*) as count FROM clothing_items')
        stats['items_count'] = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM materials')
        stats['materials_count'] = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM environmental_impacts')
        stats['impacts_count'] = cursor.fetchone()['count']
        
        # Get unique brands
        cursor.execute('SELECT COUNT(DISTINCT brand) as count FROM clothing_items WHERE brand IS NOT NULL')
        stats['brands_count'] = cursor.fetchone()['count']
        
        # Get unique categories
        cursor.execute('SELECT COUNT(DISTINCT category) as count FROM clothing_items WHERE category IS NOT NULL')
        stats['categories_count'] = cursor.fetchone()['count']
        
        # Get unique impact categories
        cursor.execute('SELECT COUNT(DISTINCT impact_category) as count FROM environmental_impacts')
        stats['impact_categories_count'] = cursor.fetchone()['count']
        
        # Get average weight
        cursor.execute('SELECT AVG(weight_grams) as avg_weight FROM clothing_items')
        avg_weight = cursor.fetchone()['avg_weight']
        stats['avg_weight'] = round(avg_weight, 1) if avg_weight else 0
        
        conn.close()
        return stats
    
    def search_items(self, search_term):
        """Search clothing items by name, brand, category, or QR code"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term.lower()}%"
        cursor.execute('''
        SELECT * FROM clothing_items 
        WHERE LOWER(qr_code) LIKE ? 
           OR LOWER(item_name) LIKE ? 
           OR LOWER(brand) LIKE ? 
           OR LOWER(category) LIKE ?
        ORDER BY item_name
        ''', (search_pattern, search_pattern, search_pattern, search_pattern))
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    def search_materials(self, search_term):
        """Search materials by name or description"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term.lower()}%"
        cursor.execute('''
        SELECT m.*, COUNT(ei.impact_id) as impact_count
        FROM materials m
        LEFT JOIN environmental_impacts ei ON m.material_id = ei.material_id
        WHERE LOWER(m.material_name) LIKE ? 
           OR LOWER(m.description) LIKE ?
        GROUP BY m.material_id
        ORDER BY m.material_name
        ''', (search_pattern, search_pattern))
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_material_usage_count(self, material_id):
        """Get how many clothing items use this material"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT COUNT(*) as count FROM clothing_material_composition 
        WHERE material_id = ?
        ''', (material_id,))
        
        result = cursor.fetchone()['count']
        conn.close()
        return result
    
    def backup_database(self, backup_path):
        """Create a backup of the database"""
        import shutil
        try:
            shutil.copy2(self.db_path, backup_path)
            return True
        except Exception:
            return False
    
    def validate_material_composition(self, qr_code):
        """Validate that material composition adds up to 100%"""
        materials = self.get_material_composition(qr_code)
        total_percentage = sum(material['percentage'] for material in materials)
        return abs(total_percentage - 100) < 0.1  # Allow small rounding errors
    
    def get_items_by_material(self, material_name):
        """Get all clothing items that contain a specific material"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT ci.*, cmc.percentage
        FROM clothing_items ci
        JOIN clothing_material_composition cmc ON ci.qr_code = cmc.qr_code
        JOIN materials m ON cmc.material_id = m.material_id
        WHERE m.material_name = ?
        ORDER BY ci.item_name
        ''', (material_name.lower(),))
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    def close(self):
        """Close database connection (compatibility method)"""
        # Since we use get_connection() pattern, individual connections are closed in methods
        pass

# Initialize database
db = FashionEnvironmentDB()

@app.route('/', methods=['GET'])
def username_page():
    if 'username' in session:
        return redirect(url_for('index'))
    return render_template('username.html')

@app.route('/set_username', methods=['POST'])
def set_username():
    username = request.form.get('username')
    if username:
        session['username'] = username
        # Save username to the database if not already present
        conn = sqlite3.connect('fashion_env.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE)''')
        cursor.execute('''INSERT OR IGNORE INTO users (username) VALUES (?)''', (username,))
        conn.commit()
        conn.close()
        return redirect(url_for('slider'))
    return redirect(url_for('username_page'))

@app.route('/index')
def index():
    username = session.get('username')
    if not username:
        return redirect(url_for('slider'))
    """Main page with QR scanner"""
    return render_template('index.html', username=username)

@app.route('/api/analyze/<qr_code>')
def analyze_item(qr_code):
    """API endpoint to analyze clothing item - same logic as your desktop app"""
    try:
        # Get clothing item
        item = db.get_clothing_item(qr_code)
        if not item:
            return jsonify({
                'error': True,
                'message': f'No item found with QR code: {qr_code}',
                'available_items': [dict(item) for item in db.list_all_clothing_items()]
            })
        
        # Get material composition
        materials = db.get_material_composition(qr_code)
        
        # Calculate environmental impacts - exact same logic as your desktop app
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
                impact_data = db.get_environmental_impact(material['material_name'], category)
                if impact_data:
                    # Same calculation as your desktop app
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
                # Remove /kg from final unit display (same as your desktop app fix)
                final_unit = unit.replace('/kg', '')
                total_impacts[category] = {
                    'value': category_total, 
                    'unit': final_unit,
                    'name': category_names[category],
                    'materials': material_impacts
                }
        
        results['impacts'] = total_impacts
        
        # Add tube scale calculation
        water_usage = total_impacts.get('water_usage', {}).get('value', 0)
        results['tube_scale'] = calculate_tube_scale(water_usage)
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)})

def calculate_tube_scale(water_liters):
    """Convert water usage to tube scale (0.7L = 0.06ml, 4800L = 400ml)"""
    if water_liters <= 0:
        return 0
    
    # Scale mapping: 4800L = 400ml, so 1L = 0.0833ml on tube scale
    tube_volume = water_liters * (400 / 4800)
    return round(tube_volume, 2)



@app.route('/api/items')
def get_all_items():
    """Get all clothing items for database view"""
    try:
        items = db.list_all_clothing_items()
        return jsonify([dict(item) for item in items])
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)})

def normalize(value, best, worst):
    if worst == best:
        return 1.0
    return max(0, min(1, (worst - value) / (worst - best)))

@app.route("/cart")
def cart():
    username = session.get('username')
    if not username:
        return redirect(url_for('username_page'))
    
    cart_items = session.get('cart_items', [])
    summary = {
        "subtotal": "0.00",
        "total": "0.00",
        "free_shipping_threshold": "22.01"
    }

    minmax = {
        'water_usage': (5.91996, 6000),
        'carbon_footprint': (0.9, 10.4),
        'energy_usage': (1.09323, 138)
    }
    
    def get_item_score(qr_code):
        impacts = {}
        item = db.get_clothing_item(qr_code)
        if not item:
            return None
        materials = db.get_material_composition(qr_code)
        for category in minmax:
            total = 0
            for mat in materials:
                impact_data = db.get_environmental_impact(mat['material_name'], category)
                if impact_data:
                    total += impact_data['impact_value'] * (mat['percentage']/100) * (item['weight_grams']/1000)
            impacts[category] = total
        scores = [normalize(impacts[cat], minmax[cat][0], minmax[cat][1]) for cat in minmax]
        return sum(scores) / len(scores) * 100
    
    item_scores = []
    if cart_items:
        for item in cart_items:
            score = get_item_score(item['qr_code'])
            if score is not None:
                item_scores.append({'name': item['name'], 'score': round(score, 1)})
        scores = [s['score'] for s in item_scores]
        if scores:
            sustainability_score = round(sum(scores) / len(scores), 1)
        else:
            sustainability_score = None
    else:
        sustainability_score = None
    
    return render_template("cart.html", cart_items=cart_items, summary=summary, hide_nav=True, username=username, sustainability_score=sustainability_score, item_scores=item_scores)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('username_page'))

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """Unified route to handle both form submissions and JSON requests for adding items to cart"""
    
    username = session.get('username')
    if not username:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Please log in first'})
        else:
            return redirect(url_for('username_page'))
    
    # Initialize cart in session if it doesn't exist
    if 'cart_items' not in session:
        session['cart_items'] = []
    
    # Check if cart already has 3 items
    if len(session['cart_items']) >= 3:
        return jsonify({'success': False, 'message': 'Maximum 3 items allowed in cart'})
    
    # Handle different request types
    if request.is_json:
        # JSON request (from QR scanner)
        data = request.json
        qr_code = data.get('qr_code')
        
        if not qr_code:
            return jsonify({'success': False, 'message': 'No QR code provided'})
        
        try:
            # Check if item already in cart
            if any(cart_item['qr_code'] == qr_code for cart_item in session['cart_items']):
                return jsonify({'success': False, 'message': 'Item already in cart'})
            
            # Get item details directly from database
            item_details = get_item_details_by_qr(qr_code)
            
            if not item_details:
                return jsonify({'success': False, 'message': 'Item not found'})
            
            # Create cart item with fetched details
            cart_item = {
                'name': item_details['item_name'],
                'qr_code': qr_code,
                'impact': f"{item_details['weight_grams']}g",
                'price': '0.00',
                'quantity': 1,
                'brand': item_details.get('brand', ''),
                'category': item_details.get('category', ''),
                'options': []
            }
            
            session['cart_items'].append(cart_item)
            session.modified = True
            
            # Check if this was the first item added
            is_first_item = len(session['cart_items']) == 1
            
            return jsonify({
                'success': True, 
                'message': 'Item added to cart',
                'item_name': item_details['item_name'],
                'redirect_to_cart': is_first_item  # Redirect if first item
            })
            
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error adding item: {str(e)}'})
    
    else:
        # Form request (your existing functionality)
        item_name = request.form.get('item_name')
        qr_code = request.form.get('qr_code')
        environmental_impact = request.form.get('environmental_impact')
        
        if not item_name or not qr_code:
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        # Check if item already in cart
        if any(cart_item['qr_code'] == qr_code for cart_item in session['cart_items']):
            return jsonify({'success': False, 'message': 'Item already in cart'})
        
        # Create cart item from form data
        cart_item = {
            'name': item_name,
            'qr_code': qr_code,
            'impact': environmental_impact,
            'price': '0.00',
            'quantity': 1,
            'options': []
        }
        
        session['cart_items'].append(cart_item)
        session.modified = True
        
        return jsonify({'success': True, 'message': 'Item added to cart'})


def get_item_details_by_qr(qr_code):
    """
    Helper function to get item details by QR code using your existing database setup
    """
    try:
        # Use your existing database instance
        item = db.get_clothing_item(qr_code)
        
        if item:
            # Convert sqlite3.Row to dict to use .get() method
            item_dict = dict(item)
            return {
                'qr_code': item_dict['qr_code'],
                'item_name': item_dict['item_name'],
                'brand': item_dict.get('brand', ''),
                'category': item_dict.get('category', ''),
                'weight_grams': item_dict['weight_grams'],
                'created_date': item_dict.get('created_date', '')
            }
        else:
            return None
            
    except Exception as e:
        print(f"Database error: {e}")
        return None



@app.route('/api/suggestions/<query>')
def get_suggestions(query):
    """Get QR code suggestions based on user input"""
    try:
        # Get all clothing items from database
        items = db.list_all_clothing_items()
        
        # Filter items that match the query (case-insensitive)
        suggestions = []
        query_lower = query.lower()
        
        for item in items:
            if (query_lower in item['qr_code'].lower() or 
                query_lower in item['item_name'].lower()):
                suggestions.append({
                    'qr_code': item['qr_code'],
                    'item_name': item['item_name']
                })
        
        return jsonify({'suggestions': suggestions[:5]})  # Limit to 5 suggestions
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    """Remove an item from the cart"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'})
    
    try:
        data = request.get_json()
        item_name = data.get('item_name')
        
        if not item_name:
            return jsonify({'success': False, 'message': 'Item name is required'})
        
        # Get current cart
        cart = session.get('cart_items', [])
        
        # Find and remove the item
        original_length = len(cart)
        cart = [item for item in cart if item['name'] != item_name]
        
        if len(cart) == original_length:
            return jsonify({'success': False, 'message': 'Item not found in cart'})
        
        # Update session
        session['cart_items'] = cart
        
        return jsonify({'success': True, 'message': 'Item removed from cart'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error removing item: {str(e)}'})

@app.route('/save_choice', methods=['POST'])
def save_choice():
    data = request.get_json()
    session['last_choice'] = data
    session.modified = True
    return jsonify({'success': True})

@app.route('/get_last_choice')
def get_last_choice():
    return jsonify(session.get('last_choice', {}))

@app.route('/save_current_choice_for_receipt', methods=['POST'])
def save_current_choice_for_receipt():
    """Save the current cart details and shift the previous one."""
    # If a 'current' choice exists in the session, move it to become the 'previous' choice.
    if 'current_choice_for_receipt' in session:
        session['prev_choice_for_receipt'] = session['current_choice_for_receipt']
    
    # Save the new data, which was just sent from the cart, as the new 'current' choice.
    data = request.get_json()
    session['current_choice_for_receipt'] = data
    session.modified = True
    return jsonify({'success': True})

@app.route('/receipt')
def receipt():
    username = session.get('username')
    if not username:
        return redirect(url_for('username_page'))
        
    current_choice = session.get('current_choice_for_receipt', {})
    prev_choice = session.get('prev_choice_for_receipt', {})
    
    # Get the current date and time to display on the receipt
    date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
    return render_template(
        'receipt.html', 
        current_choice=current_choice, 
        prev_choice=prev_choice,
        username=username, 
        date=date_str,
        hide_nav=True
    )

@app.route('/slider')
def slider():
    username = session.get('username')
    if not username:
        # If no user, send them to login first
        return redirect(url_for('username_page'))
    # hide_nav is used in base.html to conditionally hide the navigation bar
    return render_template('slider.html', username=username, hide_nav=True)

@app.route('/care', methods=['GET', 'POST'])
def care():
    username = session.get('username')
    if not username:
        return redirect(url_for('username_page'))

    if request.method == 'POST':
        wear_frequency = request.form.get('wear_frequency')
        wash_frequency = request.form.get('wash_frequency')
        
        # Save to database
        try:
            conn = sqlite3.connect('fashion_env.db')
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_care_habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    wear_frequency INTEGER,
                    wash_frequency TEXT,
                    initial_score INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Get the initial score from session
            initial_score = session.get('initial_score', 0)
            
            # Insert or update the user's care habits
            cursor.execute('''
                INSERT OR REPLACE INTO user_care_habits 
                (username, wear_frequency, wash_frequency, initial_score) 
                VALUES (?, ?, ?, ?)
            ''', (username, wear_frequency, wash_frequency, initial_score))
            
            conn.commit()
            conn.close()
            
            flash('Your care habits have been saved successfully!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            print(f"Error saving care habits: {e}")
            flash('Error saving your habits. Please try again.', 'error')
            return redirect(url_for('care'))

    return render_template('care.html', hide_nav=True, username=username)

@app.route('/save_score', methods=['POST'])
def save_score():
    data = request.get_json()
    score = data.get('score')
    username = session.get('username')

    if score is None or username is None:
        return jsonify({'status': 'error', 'message': 'Missing score or user information.'}), 400

    session['initial_score'] = score
    
    print(f"Received score from {username}: {score}%. Stored in session.")

    return jsonify({'status': 'success', 'message': f'Initial score of {score} saved for user {username}.'})

@app.route('/api/cart_summary')
def api_cart_summary():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    cart_items = session.get('cart_items', [])
    minmax = {
        'water_usage': (5.91996, 6000),
        'carbon_footprint': (0.9, 10.4),
        'energy_usage': (1.09323, 138)
    }
    def get_item_score(qr_code):
        impacts = {}
        item = db.get_clothing_item(qr_code)
        if not item:
            return None
        materials = db.get_material_composition(qr_code)
        for category in minmax:
            total = 0
            for mat in materials:
                impact_data = db.get_environmental_impact(mat['material_name'], category)
                if impact_data:
                    total += impact_data['impact_value'] * (mat['percentage']/100) * (item['weight_grams']/1000)
            impacts[category] = total
        scores = [normalize(impacts[cat], minmax[cat][0], minmax[cat][1]) for cat in minmax]
        return sum(scores) / len(scores) * 100
    item_scores = []
    if cart_items:
        for item in cart_items:
            score = get_item_score(item['qr_code'])
            if score is not None:
                item_scores.append({'name': item['name'], 'score': round(score, 1)})
        scores = [s['score'] for s in item_scores]
        if scores:
            sustainability_score = round(sum(scores) / len(scores), 1)
        else:
            sustainability_score = None
    else:
        sustainability_score = None
    return jsonify({
        'sustainability_score': sustainability_score,
        'item_scores': item_scores
    })

# Materials API endpoints
@app.route('/api/materials', methods=['GET'])
def get_all_materials():
    """Get all materials with impact counts"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get materials with impact counts
        cursor.execute('''
        SELECT m.*, 
               COUNT(ei.impact_id) as impact_count
        FROM materials m
        LEFT JOIN environmental_impacts ei ON m.material_id = ei.material_id
        GROUP BY m.material_id, m.material_name, m.density_g_per_cm3, m.description
        ORDER BY m.material_name
        ''')
        
        materials = cursor.fetchall()
        conn.close()
        
        return jsonify([dict(material) for material in materials])
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/api/materials', methods=['POST'])
def add_material():
    """Add a new material"""
    try:
        data = request.get_json()
        
        name = data.get('name', '').strip().lower()
        density = data.get('density')
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'error': True, 'message': 'Material name is required'}), 400
        
        # Convert empty strings to None
        density = density if density else None
        description = description if description else None
        
        material_id = db.add_material(name, density, description)
        
        if material_id:
            return jsonify({'success': True, 'material_id': material_id})
        else:
            return jsonify({'error': True, 'message': 'Material already exists or invalid data'}), 400
            
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/api/materials/<int:material_id>', methods=['PUT'])
def update_material(material_id):
    """Update an existing material"""
    try:
        data = request.get_json()
        
        name = data.get('name', '').strip().lower()
        density = data.get('density')
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'error': True, 'message': 'Material name is required'}), 400
        
        # Convert empty strings to None
        density = density if density else None
        description = description if description else None
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE materials 
        SET material_name=?, density_g_per_cm3=?, description=?
        WHERE material_id=?
        ''', (name, density, description, material_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/api/materials/<int:material_id>', methods=['DELETE'])
def delete_material(material_id):
    """Delete a material and its associated data"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if material is used in clothing items
        cursor.execute('''
        SELECT COUNT(*) as count FROM clothing_material_composition 
        WHERE material_id = ?
        ''', (material_id,))
        usage_count = cursor.fetchone()['count']
        
        # Delete environmental impacts first
        cursor.execute("DELETE FROM environmental_impacts WHERE material_id = ?", (material_id,))
        
        # Delete material compositions
        cursor.execute("DELETE FROM clothing_material_composition WHERE material_id = ?", (material_id,))
        
        # Delete material
        cursor.execute("DELETE FROM materials WHERE material_id = ?", (material_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'affected_items': usage_count})
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

# Material composition endpoints
@app.route('/api/materials/<qr_code>')
def get_item_materials(qr_code):
    """Get material composition for a specific item"""
    try:
        materials = db.get_material_composition(qr_code)
        return jsonify([dict(material) for material in materials])
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

# Environmental impacts API endpoints
@app.route('/api/impacts', methods=['GET'])
def get_all_impacts():
    """Get all environmental impacts"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT ei.impact_id, m.material_name, ei.impact_category, 
               ei.impact_value, ei.unit, ei.source
        FROM environmental_impacts ei
        JOIN materials m ON ei.material_id = m.material_id
        ORDER BY m.material_name, ei.impact_category
        ''')
        
        impacts = cursor.fetchall()
        conn.close()
        
        return jsonify([dict(impact) for impact in impacts])
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/api/impacts', methods=['POST'])
def add_impact():
    """Add a new environmental impact"""
    try:
        data = request.get_json()
        
        material_name = data.get('material_name', '').strip().lower()
        impact_category = data.get('impact_category', '').strip()
        impact_value = data.get('impact_value')
        unit = data.get('unit', '').strip()
        source = data.get('source', '').strip()
        
        if not all([material_name, impact_category, impact_value is not None, unit]):
            return jsonify({'error': True, 'message': 'All fields except source are required'}), 400
        
        # Get material ID
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name,))
        material = cursor.fetchone()
        
        if not material:
            conn.close()
            return jsonify({'error': True, 'message': f'Material "{material_name}" not found'}), 404
        
        # Convert empty string to None for source
        source = source if source else None
        
        cursor.execute('''
        INSERT INTO environmental_impacts (material_id, impact_category, impact_value, unit, source)
        VALUES (?, ?, ?, ?, ?)
        ''', (material['material_id'], impact_category, impact_value, unit, source))
        
        impact_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'impact_id': impact_id})
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/api/impacts/<int:impact_id>', methods=['PUT'])
def update_impact(impact_id):
    """Update an existing environmental impact"""
    try:
        data = request.get_json()
        
        material_name = data.get('material_name', '').strip().lower()
        impact_category = data.get('impact_category', '').strip()
        impact_value = data.get('impact_value')
        unit = data.get('unit', '').strip()
        source = data.get('source', '').strip()
        
        if not all([material_name, impact_category, impact_value is not None, unit]):
            return jsonify({'error': True, 'message': 'All fields except source are required'}), 400
        
        # Get material ID
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name,))
        material = cursor.fetchone()
        
        if not material:
            conn.close()
            return jsonify({'error': True, 'message': f'Material "{material_name}" not found'}), 404
        
        # Convert empty string to None for source
        source = source if source else None
        
        cursor.execute('''
        UPDATE environmental_impacts 
        SET material_id=?, impact_category=?, impact_value=?, unit=?, source=?
        WHERE impact_id=?
        ''', (material['material_id'], impact_category, impact_value, unit, source, impact_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/api/impacts/<int:impact_id>', methods=['DELETE'])
def delete_impact(impact_id):
    """Delete an environmental impact"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM environmental_impacts WHERE impact_id = ?", (impact_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

# Clothing items CRUD endpoints
@app.route('/api/items', methods=['POST'])
def add_clothing_item():
    try:
        data = request.get_json()
        print(f"Raw request data: {data}")  # Debug print
        
        # Check if data is None
        if data is None:
            return jsonify({'error': True, 'message': 'No JSON data received'}), 400
        
        # Handle None values properly with extra safety
        qr_code = str(data.get('qr_code') or '').strip()
        name = str(data.get('name') or '').strip()
        brand = str(data.get('brand') or '').strip()
        category = str(data.get('category') or '').strip()
        weight = data.get('weight')
        materials = data.get('materials', [])
        
        print(f"Parsed data - QR: {qr_code}, Name: {name}, Weight: {weight}")  # Debug
        print(f"Materials: {materials}")  # Debug
        
        if not qr_code or not name or not weight:
            return jsonify({'error': True, 'message': 'QR code, name, and weight are required'}), 400
        
        # Convert empty strings to None
        brand = brand if brand else None
        category = category if category else None
        
        # Add clothing item
        success = db.add_clothing_item(qr_code, name, int(weight), brand, category)
        
        if not success:
            return jsonify({'error': True, 'message': 'QR code already exists'}), 400
        
        # Add material composition with better error handling
        if materials:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            for i, material_data in enumerate(materials):
                print(f"Processing material {i}: {material_data}")  # Debug
                
                if material_data is None:
                    continue
                    
                material_name = str(material_data.get('material_name') or '').strip().lower()
                percentage = material_data.get('percentage')
                
                print(f"Material name: {material_name}, Percentage: {percentage}")  # Debug
                
                if material_name and percentage and float(percentage) > 0:
                    # Get material ID
                    cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name,))
                    material = cursor.fetchone()
                    
                    if material:
                        cursor.execute('''
                        INSERT INTO clothing_material_composition (qr_code, material_id, percentage)
                        VALUES (?, ?, ?)
                        ''', (qr_code, material['material_id'], float(percentage)))
                        print(f"Added material composition: {material_name} - {percentage}%")
            
            conn.commit()
            conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        import traceback
        print(f"Full error traceback:")
        print(traceback.format_exc())
        return jsonify({'error': True, 'message': str(e)}), 500
    
@app.route('/api/items/<qr_code>', methods=['PUT'])
def update_clothing_item(qr_code):
    """Update an existing clothing item"""
    try:
        data = request.get_json()
        
        name = data.get('name', '').strip()
        brand = data.get('brand', '').strip()
        category = data.get('category', '').strip()
        weight = data.get('weight')
        materials = data.get('materials', [])
        
        if not all([name, weight]):
            return jsonify({'error': True, 'message': 'Name and weight are required'}), 400
        
        # Convert empty strings to None
        brand = brand if brand else None
        category = category if category else None
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Update item details
        cursor.execute('''
        UPDATE clothing_items 
        SET item_name=?, brand=?, category=?, weight_grams=?
        WHERE qr_code=?
        ''', (name, brand, category, weight, qr_code))
        
        # Delete old material composition
        cursor.execute('DELETE FROM clothing_material_composition WHERE qr_code=?', (qr_code,))
        
        # Add new material composition
        for material_data in materials:
            material_name = material_data.get('material_name', '').strip().lower()
            percentage = material_data.get('percentage')
            
            if material_name and percentage and percentage > 0:
                # Get material ID
                cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name,))
                material = cursor.fetchone()
                
                if material:
                    cursor.execute('''
                    INSERT INTO clothing_material_composition (qr_code, material_id, percentage)
                    VALUES (?, ?, ?)
                    ''', (qr_code, material['material_id'], percentage))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/api/items/<qr_code>', methods=['DELETE'])
def delete_clothing_item(qr_code):
    """Delete a clothing item and its material composition"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Delete material composition first (foreign key constraint)
        cursor.execute("DELETE FROM clothing_material_composition WHERE qr_code = ?", (qr_code,))
        
        # Delete clothing item
        cursor.execute("DELETE FROM clothing_items WHERE qr_code = ?", (qr_code,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

# Enhanced database route to serve the new page
@app.route('/database')
def database_management():
    """Enhanced database management page"""
    username = session.get('username')
    if not username:
        return redirect(url_for('username_page'))
    
    return render_template('database_management.html', username=username)

# Additional utility endpoints for database stats
@app.route('/api/stats/overview')
def get_database_overview():
    """Get overview statistics for the database"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get counts
        cursor.execute('SELECT COUNT(*) as count FROM clothing_items')
        items_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM materials')
        materials_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM environmental_impacts')
        impacts_count = cursor.fetchone()['count']
        
        # Get unique brands
        cursor.execute('SELECT COUNT(DISTINCT brand) as count FROM clothing_items WHERE brand IS NOT NULL')
        brands_count = cursor.fetchone()['count']
        
        # Get unique categories
        cursor.execute('SELECT COUNT(DISTINCT category) as count FROM clothing_items WHERE category IS NOT NULL')
        categories_count = cursor.fetchone()['count']
        
        # Get unique impact categories
        cursor.execute('SELECT COUNT(DISTINCT impact_category) as count FROM environmental_impacts')
        impact_categories_count = cursor.fetchone()['count']
        
        # Get average weight
        cursor.execute('SELECT AVG(weight_grams) as avg_weight FROM clothing_items')
        avg_weight = cursor.fetchone()['avg_weight'] or 0
        
        conn.close()
        
        return jsonify({
            'items_count': items_count,
            'materials_count': materials_count,
            'impacts_count': impacts_count,
            'brands_count': brands_count,
            'categories_count': categories_count,
            'impact_categories_count': impact_categories_count,
            'avg_weight': round(avg_weight, 1) if avg_weight else 0
        })
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500



@app.route('/api/cart')
def get_cart():
    """Get current cart items for display"""
    cart_items = session.get('cart_items', [])
    return jsonify({
        'success': True,
        'items': cart_items
    })
# Add this single endpoint to your app.py

@app.route('/api/esp32', methods=['POST'])
def receive_esp32_word():
    """Receive a single word from ESP32"""
    try:
        # Get the word from POST data
        if request.is_json:
            data = request.get_json()
            word = data.get('word', '').strip()
        else:
            word = request.form.get('word', '').strip()
        
        if not word:
            return jsonify({'error': 'No word received'}), 400
        
        # Log the received word
        print(f"ESP32 sent: {word}")
        
        # TODO: Add your logic here based on the word
        # For now, just acknowledge receipt
        
        return jsonify({
            'success': True, 
            'received': word,
            'message': f'Got word: {word}'
        })
        
    except Exception as e:
        print(f"ESP32 endpoint error: {e}")
        return jsonify({'error': str(e)}), 500


# Integration with Flask app
def integrate_enhanced_scoring(app, db):
    """Add enhanced scoring endpoints to Flask app"""
    scorer = EnhancedSustainabilityScorer(db)
    
    @app.route('/api/enhanced_analyze/<qr_code>')
    def enhanced_analyze_item(qr_code):
        try:
            result = scorer.get_item_detailed_score(qr_code)
            if result:
                return jsonify(result)
            else:
                return jsonify({'error': 'Item not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/enhanced_cart_summary')
    def enhanced_cart_summary():
        username = session.get('username')
        if not username:
            return jsonify({'error': 'Not logged in'}), 401
            
        cart_items = session.get('cart_items', [])
        if not cart_items:
            return jsonify({'error': 'Empty cart'}), 400
            
        try:
            result = scorer.calculate_cart_score(cart_items)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/sustainability_config')
    def get_sustainability_config():
        """Return current scoring configuration for transparency"""
        return jsonify({
            'category_weights': scorer.config.category_weights,
            'material_bonuses': scorer.config.material_sustainability_bonus,
            'material_penalties': scorer.config.material_sustainability_penalty,
            'category_multipliers': scorer.config.category_multipliers
        })
    

@app.route('/api/debug_enhanced_scoring')
def debug_enhanced_scoring():
    """Debug route to test enhanced scoring"""
    try:
        username = session.get('username')
        cart_items = session.get('cart_items', [])
        
        # Basic checks
        debug_info = {
            'username': username,
            'cart_items_count': len(cart_items),
            'cart_items': cart_items,
            'session_keys': list(session.keys())
        }
        
        if not username:
            debug_info['error'] = 'No username in session'
            return jsonify(debug_info)
        
        if not cart_items:
            debug_info['error'] = 'No cart items'
            return jsonify(debug_info)
        
        # Test if the enhanced scoring class can be created
        try:
            scorer = EnhancedSustainabilityScorer(db)
            debug_info['scorer_created'] = True
        except Exception as e:
            debug_info['scorer_error'] = str(e)
            return jsonify(debug_info)
        
        # Test each cart item individually
        item_tests = []
        for i, cart_item in enumerate(cart_items):
            qr_code = cart_item.get('qr_code')
            item_test = {
                'index': i,
                'qr_code': qr_code,
                'item_name': cart_item.get('name')
            }
            
            # Check if item exists in database
            try:
                db_item = db.get_clothing_item(qr_code)
                if db_item:
                    item_test['db_item_found'] = True
                    item_test['db_item'] = dict(db_item)
                else:
                    item_test['db_item_found'] = False
                    item_test['error'] = 'Item not found in database'
                    item_tests.append(item_test)
                    continue
            except Exception as e:
                item_test['db_error'] = str(e)
                item_tests.append(item_test)
                continue
            
            # Check material composition
            try:
                materials = db.get_material_composition(qr_code)
                item_test['materials_count'] = len(materials)
                item_test['materials'] = [dict(m) for m in materials]
                
                if not materials:
                    item_test['error'] = 'No material composition found'
                    item_tests.append(item_test)
                    continue
            except Exception as e:
                item_test['materials_error'] = str(e)
                item_tests.append(item_test)
                continue
            
            # Test enhanced scoring for this item
            try:
                detailed_score = scorer.get_item_detailed_score(qr_code)
                if detailed_score and 'error' not in detailed_score:
                    item_test['scoring_success'] = True
                    item_test['score'] = detailed_score['final_score']
                else:
                    item_test['scoring_error'] = detailed_score.get('error', 'Unknown scoring error')
            except Exception as e:
                item_test['scoring_exception'] = str(e)
                import traceback
                item_test['scoring_traceback'] = traceback.format_exc()
            
            item_tests.append(item_test)
        
        debug_info['item_tests'] = item_tests
        
        # Try full cart scoring if all items passed individual tests
        all_items_ok = all(item.get('scoring_success', False) for item in item_tests)
        if all_items_ok:
            try:
                result = scorer.calculate_cart_score(cart_items)
                debug_info['cart_scoring_success'] = True
                debug_info['cart_result'] = result
            except Exception as e:
                debug_info['cart_scoring_error'] = str(e)
                import traceback
                debug_info['cart_scoring_traceback'] = traceback.format_exc()
        else:
            debug_info['cart_scoring_skipped'] = 'Some items failed individual tests'
        
        return jsonify(debug_info)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': True,
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500
    
# Error handling middleware
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': True, 'message': 'Endpoint not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': True, 'message': 'Internal server error'}), 500
    return render_template('500.html'), 500

#esp32
# Initialize ESP32 sender (update IP address to match your ESP32)
esp32_sender = ESP32DataSender(esp32_ip="172.20.10.8", esp32_port=80)

@app.route('/api/send_to_esp32', methods=['POST'])
def send_cart_to_esp32():
    """Send current cart environmental data to ESP32 using polling method"""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    
    cart_items = session.get('cart_items', [])
    if not cart_items:
        return jsonify({'error': 'Empty cart'}), 400
    
    try:
        # Calculate environmental impacts using your existing calculation method
        if ESP32_AVAILABLE:
            # Use your existing calculation method
            impact_data = esp32_sender.calculate_cart_environmental_impact(cart_items, db)
            
            # Instead of sending directly to ESP32, store it for polling
            update_esp32_data_store(impact_data)
            
            return jsonify({
                'success': True,
                'message': 'Data stored for ESP32 polling - ESP32 will receive it within 5 seconds',
                'method': 'polling',
                'calculation_data': impact_data
            })
        else:
            return jsonify({
                'success': False,
                'message': 'ESP32 functionality not available in this deployment'
            }), 503
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/test_esp32')
def test_esp32_connection():
    """Test ESP32 connection"""
    result = esp32_sender.test_connection()
    return jsonify(result)

@app.route('/api/send_simple_to_esp32', methods=['POST'])
def send_simple_to_esp32():
    """Send simple values to ESP32"""
    data = request.get_json()
    
    water = data.get('water', 0)
    carbon = data.get('carbon', 0) 
    energy = data.get('energy', 0)
    
    result = esp32_sender.send_simple_values(water, carbon, energy)
    return jsonify(result)
# Add this helper function
def update_esp32_data_store(environmental_data):
    """Update the data store with new environmental data"""
    with data_store_lock:
        esp32_data_store['environmental_data'] = environmental_data.copy()
        esp32_data_store['has_new_data'] = True
        esp32_data_store['last_updated'] = datetime.now()
    
    print(f"ESP32 data store updated: {environmental_data}")

# Add the ESP32 polling endpoint
@app.route('/api/esp32_poll', methods=['GET'])
def esp32_poll():
    """Endpoint for ESP32 to poll for new environmental data"""
    
    with data_store_lock:
        current_time = datetime.now()
        esp32_data_store['last_polled'] = current_time
        
        if esp32_data_store['has_new_data'] and esp32_data_store['environmental_data']:
            # Return the environmental data
            response_data = {
                'has_new_data': True,
                'water_liters': esp32_data_store['environmental_data'].get('water_usage', 0),
                'carbon_kg': esp32_data_store['environmental_data'].get('carbon_footprint', 0),
                'energy_mj': esp32_data_store['environmental_data'].get('energy_usage', 0),
                'item_count': esp32_data_store['environmental_data'].get('item_count', 0),
                'timestamp': int(time.time())
            }
            
            # Mark as delivered (ESP32 has received it)
            esp32_data_store['has_new_data'] = False
            
            print(f"ESP32 polled - sending new data: {response_data}")
            return jsonify(response_data)
        else:
            # No new data available
            return jsonify({'has_new_data': False}), 204
        
if __name__ == '__main__':
    initialize_all_scorers()

    app.run(debug=True)