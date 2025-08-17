import json
import os
from typing import List, Dict, Any, Optional, Tuple

def load_sectors() -> List[Dict[str, Any]]:
    """Load sectors from the JSON file"""
    try:
        if os.path.exists('sector.json'):
            with open('sector.json', 'r') as file:
                return json.load(file)
        else:
            return []
    except Exception as e:
        print(f"Error loading sectors: {e}")
        return []

def save_sectors(sectors: List[Dict[str, Any]]) -> bool:
    """Save sectors to the JSON file"""
    try:
        with open('sector.json', 'w') as file:
            json.dump(sectors, file, indent=2)
        return True
    except Exception as e:
        print(f"Error saving sectors: {e}")
        return False

def get_sectors_with_filters(filter_text: str = "") -> Dict[str, Any]:
    """Get sectors with filtering (no pagination)"""
    sectors = load_sectors()
    
    # Apply filters
    filtered_sectors = sectors
    
    if filter_text:
        filtered_sectors = [s for s in sectors if filter_text.lower() in s.get('sector', '').lower()]
    
    return {
        'results': filtered_sectors,
        'total': len(filtered_sectors)
    }

def add_sector_to_file(sector: str) -> Tuple[bool, str]:
    """Add a new sector to the file"""
    try:
        sectors = load_sectors()
        
        # Check if sector already exists
        if any(s.get('sector', '').lower() == sector.lower() for s in sectors):
            return False, f"Sector '{sector}' already exists"
        
        new_sector = {
            'sector': sector
        }
        
        sectors.append(new_sector)
        
        if save_sectors(sectors):
            return True, f"Sector '{sector}' added successfully"
        else:
            return False, "Failed to save sectors"
            
    except Exception as e:
        return False, f"Error adding sector: {str(e)}"

def update_sector_in_file(old_sector: str, new_sector: str) -> Tuple[bool, str]:
    """Update a sector in the file"""
    try:
        sectors = load_sectors()
        
        # Find the sector to update
        sector_index = None
        for i, s in enumerate(sectors):
            if s.get('sector', '').lower() == old_sector.lower():
                sector_index = i
                break
        
        if sector_index is None:
            return False, f"Sector '{old_sector}' not found"
        
        # Check if new sector name already exists
        if any(s.get('sector', '').lower() == new_sector.lower() for s in sectors):
            return False, f"Sector '{new_sector}' already exists"
        
        # Update the sector
        sectors[sector_index] = {
            'sector': new_sector
        }
        
        if save_sectors(sectors):
            return True, f"Sector '{old_sector}' updated successfully to '{new_sector}'"
        else:
            return False, "Failed to save sectors"
            
    except Exception as e:
        return False, f"Error updating sector: {str(e)}"

def delete_sector_from_file(sector: str) -> Tuple[bool, str]:
    """Delete a sector from the file"""
    try:
        sectors = load_sectors()
        
        # Find and remove the sector
        original_count = len(sectors)
        sectors = [s for s in sectors if s.get('sector', '').lower() != sector.lower()]
        
        if len(sectors) == original_count:
            return False, f"Sector '{sector}' not found"
        
        if save_sectors(sectors):
            return True, f"Sector '{sector}' deleted successfully"
        else:
            return False, "Failed to save sectors"
            
    except Exception as e:
        return False, f"Error deleting sector: {str(e)}"
