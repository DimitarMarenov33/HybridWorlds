#!/usr/bin/env python3
"""
Environmental Data Cleanup Script
Resolves conflicts in environmental impact data by prioritizing reliable sources
"""

import sqlite3
from database_setup import FashionEnvironmentDB

def analyze_data_conflicts():
    """Analyze and show data conflicts in the database"""
    print("🔍 Analyzing environmental impact data conflicts...")
    
    db = FashionEnvironmentDB()
    cursor = db.conn.cursor()
    
    # Find materials with multiple values for the same impact category
    cursor.execute('''
    SELECT 
        m.material_name,
        ei.impact_category,
        COUNT(*) as count,
        GROUP_CONCAT(ei.impact_value || ' (' || ei.source || ')') as all_values
    FROM environmental_impacts ei
    JOIN materials m ON ei.material_id = m.material_id
    GROUP BY m.material_name, ei.impact_category
    HAVING COUNT(*) > 1
    ORDER BY m.material_name, ei.impact_category
    ''')
    
    conflicts = cursor.fetchall()
    
    if conflicts:
        print(f"\n⚠️ Found {len(conflicts)} conflicts:")
        for conflict in conflicts:
            print(f"\n📝 {conflict['material_name']} - {conflict['impact_category']}:")
            print(f"   {conflict['all_values']}")
    else:
        print("✅ No conflicts found!")
    
    db.close()
    return conflicts

def prioritize_sources():
    """Clean up conflicts by prioritizing most reliable sources"""
    print("\n🔧 Resolving conflicts using source priority...")
    
    # Define source reliability priority (higher number = more reliable)
    source_priority = {
        'Textile Exchange 2017': 10,  # Industry standard
        'Ecoinvent 3.0': 9,          # Scientific database
        'Higg MSI': 8,               # Industry sustainability index
        'European Flax': 7,          # Regional authority
        'Plastic Textiles Industry Dataset': 6,  # Your imported data
        'Sample data for demonstration': 1       # Sample data (lowest priority)
    }
    
    db = FashionEnvironmentDB()
    cursor = db.conn.cursor()
    
    # Get all impacts with their priority scores
    cursor.execute('''
    SELECT 
        ei.impact_id,
        m.material_name,
        ei.impact_category,
        ei.impact_value,
        ei.source,
        ROW_NUMBER() OVER (
            PARTITION BY m.material_id, ei.impact_category 
            ORDER BY ei.impact_id
        ) as row_num
    FROM environmental_impacts ei
    JOIN materials m ON ei.material_id = m.material_id
    ORDER BY m.material_name, ei.impact_category
    ''')
    
    all_impacts = cursor.fetchall()
    
    # Group by material and category
    grouped_impacts = {}
    for impact in all_impacts:
        key = (impact['material_name'], impact['impact_category'])
        if key not in grouped_impacts:
            grouped_impacts[key] = []
        grouped_impacts[key].append(impact)
    
    deleted_count = 0
    kept_count = 0
    
    # For each group, keep only the highest priority source
    for key, impacts in grouped_impacts.items():
        if len(impacts) == 1:
            kept_count += 1
            continue
            
        material_name, category = key
        print(f"\n🔄 Processing {material_name} - {category}:")
        
        # Sort by priority (highest first)
        impacts_with_priority = []
        for impact in impacts:
            priority = source_priority.get(impact['source'], 0)
            impacts_with_priority.append((impact, priority))
        
        impacts_with_priority.sort(key=lambda x: x[1], reverse=True)
        
        # Keep the highest priority one
        best_impact = impacts_with_priority[0][0]
        print(f"   ✅ Keeping: {best_impact['impact_value']} ({best_impact['source']})")
        kept_count += 1
        
        # Delete the rest
        for impact, priority in impacts_with_priority[1:]:
            cursor.execute('DELETE FROM environmental_impacts WHERE impact_id = ?', (impact['impact_id'],))
            print(f"   🗑️ Removed: {impact['impact_value']} ({impact['source']})")
            deleted_count += 1
    
    db.conn.commit()
    print(f"\n📊 Cleanup summary:")
    print(f"   ✅ Kept {kept_count} records")
    print(f"   🗑️ Deleted {deleted_count} duplicate records")
    
    db.close()

def show_final_data():
    """Show the final cleaned data"""
    print("\n📋 Final environmental impact data:")
    
    db = FashionEnvironmentDB()
    cursor = db.conn.cursor()
    
    cursor.execute('''
    SELECT 
        m.material_name,
        ei.impact_category,
        ei.impact_value,
        ei.unit,
        ei.source
    FROM environmental_impacts ei
    JOIN materials m ON ei.material_id = m.material_id
    ORDER BY m.material_name, ei.impact_category
    ''')
    
    impacts = cursor.fetchall()
    
    current_material = None
    for impact in impacts:
        if impact['material_name'] != current_material:
            current_material = impact['material_name']
            print(f"\n🧵 {current_material.upper()}:")
        
        print(f"   {impact['impact_category']}: {impact['impact_value']} {impact['unit']} ({impact['source']})")
    
    print(f"\n✅ Total: {len(impacts)} clean environmental impact records")
    db.close()

def install_missing_dependencies():
    """Install missing dependencies for Excel processing"""
    print("\n📦 Installing missing dependencies...")
    import subprocess
    import sys
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
        print("✅ Installed openpyxl for Excel file processing")
    except:
        print("⚠️ Could not install openpyxl automatically")
        print("   Please run: pip install openpyxl")

def main():
    """Main cleanup function"""
    print("🧹 Environmental Data Cleanup Tool")
    print("=" * 50)
    
    # Analyze current conflicts
    conflicts = analyze_data_conflicts()
    
    if conflicts:
        # Clean up conflicts
        prioritize_sources()
        
        # Show final clean data
        show_final_data()
        
        print("\n🎉 Data cleanup completed!")
        print("Your app now uses the most reliable environmental data available.")
    else:
        print("✅ No cleanup needed - data is already clean!")
    
    # Offer to install missing dependencies
    try:
        import openpyxl
    except ImportError:
        install_missing_dependencies()

if __name__ == "__main__":
    main()