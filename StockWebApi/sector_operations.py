import json
import logging
from utils import load_sectors, save_sectors

def get_sectors_with_filters(sector_param, page, per_page):
    """
    Get sectors with filtering and pagination
    """
    sectors = load_sectors()
    
    # Filter sectors if provided
    filtered_sectors = sectors
    if sector_param:
        filtered_sectors = [s for s in sectors if sector_param.lower() in s.get('sector', '').lower()]
    
    # Apply pagination
    total = len(filtered_sectors)
    start = (page - 1) * per_page
    end = start + per_page
    paged_sectors = filtered_sectors[start:end]
    
    return {
        'total': total,
        'page': page,
        'per_page': per_page,
        'results': paged_sectors
    }

def add_sector_to_file(sector_name):
    """
    Add a new sector to the sectors file
    """
    sectors = load_sectors()
    
    # Check if sector already exists
    if any(s.get('sector', '').lower() == sector_name.lower() for s in sectors):
        return False, "Sector already exists"
    
    sectors.append({'sector': sector_name})
    save_sectors(sectors)
    
    return True, "Sector added successfully"

def update_sector_in_file(old_sector, new_sector):
    """
    Update an existing sector in the sectors file
    """
    sectors = load_sectors()
    
    # Find and update the sector
    found = False
    for s in sectors:
        if s.get('sector', '').lower() == old_sector.lower():
            # Check if new sector name already exists
            if any(existing.get('sector', '').lower() == new_sector.lower() and existing != s for existing in sectors):
                return False, "New sector name already exists"
            s['sector'] = new_sector
            found = True
            break
    
    if not found:
        return False, "Sector not found"
    
    save_sectors(sectors)
    
    return True, "Sector updated successfully"

def delete_sector_from_file(sector_name):
    """
    Delete a sector from the sectors file
    """
    sectors = load_sectors()
    
    # Remove the sector
    new_sectors = [s for s in sectors if s.get('sector', '').lower() != sector_name.lower()]
    
    if len(new_sectors) == len(sectors):
        return False, "Sector not found"
    
    save_sectors(new_sectors)
    
    return True, "Sector deleted successfully"