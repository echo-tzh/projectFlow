# shared/navigation_config.py
from flask import request

class NavigationConfig:
    """
    Configuration for navigation structure and breadcrumbs
    """
    
    # Main navigation structure
    NAVIGATION_ITEMS = [
        {
            'title': 'Main',
            'items': [
                {
                    'name': 'Dashboard',
                    'icon': '🏠',
                    'endpoint': 'universal_dashboard.dashboard',
                    'url': None,  # Will be generated from endpoint
                    'active_patterns': ['universal_dashboard.*']
                }
            ]
        },
        {
            'title': 'Management',
            'items': [
                {
                    'name': 'Manage Course Terms',
                    'icon': '📅',
                    'endpoint': 'manage_timeframe_bp.manage_timeframes',
                    'url': None,
                    'active_patterns': ['manage_timeframe_bp.*'],
                    'children': [
                        {
                            'name': 'View All Course Terms',
                            'endpoint': 'manage_timeframe_bp.manage_timeframes',
                            'url': None
                        },
                        {
                            'name': 'Load Data',
                            'endpoint': 'load_data.select_timeframe',
                            'url': '#'
                        },
                        {
                            'name': 'Notify Users',
                            'endpoint': None,
                            'url': '#'
                        }
                    ]
                },
                {
                    'name': 'Manage Users',
                    'icon': '👥',
                    'endpoint': 'manage_users.index',  # Adjust to your actual endpoint
                    'url': '#',
                    'active_patterns': ['manage_users.*']
                },
                {
                    'name': 'Projects',
                    'icon': '📊',
                    'endpoint': 'projects.index',  # Adjust to your actual endpoint
                    'url': '#',
                    'active_patterns': ['projects.*']
                }
            ]
        },
        {
            'title': 'Settings',
            'items': [
                {
                    'name': 'System Settings',
                    'icon': '⚙️',
                    'endpoint': 'settings.system',  # Adjust to your actual endpoint
                    'url': '#',
                    'active_patterns': ['settings.system.*']
                },
                {
                    'name': 'Profile',
                    'icon': '👤',
                    'endpoint': 'profile.index',  # Adjust to your actual endpoint
                    'url': '#',
                    'active_patterns': ['profile.*']
                }
            ]
        }
    ]
    
    # Breadcrumb configuration
    BREADCRUMB_CONFIG = {
        'universal_dashboard.dashboard': [
            {'title': 'Dashboard', 'url': None}
        ],
        'manage_timeframe_bp.manage_timeframes': [
            {'title': 'Dashboard', 'url': 'universal_dashboard.dashboard'},
            {'title': 'Manage Course Terms', 'url': None}
        ],
        # Add more breadcrumb configurations as needed
    }
    
    @classmethod
    def get_navigation_items(cls):
        """Get navigation items with URLs resolved"""
        from flask import url_for
        
        def resolve_urls(items):
            resolved_items = []
            for item in items:
                resolved_item = item.copy()
                
                # Resolve main item URL
                if resolved_item.get('endpoint') and not resolved_item.get('url'):
                    try:
                        resolved_item['url'] = url_for(resolved_item['endpoint'])
                    except:
                        resolved_item['url'] = '#'
                
                # Resolve children URLs if they exist
                if 'children' in resolved_item:
                    resolved_children = []
                    for child in resolved_item['children']:
                        resolved_child = child.copy()
                        if resolved_child.get('endpoint') and not resolved_child.get('url'):
                            try:
                                resolved_child['url'] = url_for(resolved_child['endpoint'])
                            except:
                                resolved_child['url'] = '#'
                        resolved_children.append(resolved_child)
                    resolved_item['children'] = resolved_children
                
                resolved_items.append(resolved_item)
            return resolved_items
        
        resolved_navigation = []
        for section in cls.NAVIGATION_ITEMS:
            resolved_section = {
                'title': section['title'],
                'items': resolve_urls(section['items'])
            }
            resolved_navigation.append(resolved_section)
        
        return resolved_navigation
    
    @classmethod
    def get_current_nav_item(cls):
        """Get the currently active navigation item based on request endpoint"""
        current_endpoint = request.endpoint
        
        for section in cls.NAVIGATION_ITEMS:
            for item in section['items']:
                # Check if current endpoint matches this item
                if item.get('endpoint') == current_endpoint:
                    return item
                
                # Check against active patterns
                if 'active_patterns' in item:
                    for pattern in item['active_patterns']:
                        if pattern.endswith('.*'):
                            prefix = pattern[:-2]
                            if current_endpoint and current_endpoint.startswith(prefix):
                                return item
                        elif pattern == current_endpoint:
                            return item
        
        return None
    
    @classmethod
    def get_breadcrumbs(cls):
        """Get breadcrumbs for current page"""
        from flask import url_for
        
        current_endpoint = request.endpoint
        breadcrumb_config = cls.BREADCRUMB_CONFIG.get(current_endpoint, [])
        
        resolved_breadcrumbs = []
        for crumb in breadcrumb_config:
            resolved_crumb = crumb.copy()
            if resolved_crumb['url'] and not resolved_crumb['url'].startswith('http'):
                try:
                    resolved_crumb['url'] = url_for(resolved_crumb['url'])
                except:
                    resolved_crumb['url'] = '#'
            resolved_breadcrumbs.append(resolved_crumb)
        
        return resolved_breadcrumbs
    
    @classmethod
    def should_expand_section(cls, section_items):
        """Check if a navigation section should be expanded based on current page"""
        current_endpoint = request.endpoint
        
        for item in section_items:
            # Check main item
            if item.get('endpoint') == current_endpoint:
                return True
            
            # Check active patterns
            if 'active_patterns' in item:
                for pattern in item['active_patterns']:
                    if pattern.endswith('.*'):
                        prefix = pattern[:-2]
                        if current_endpoint and current_endpoint.startswith(prefix):
                            return True
                    elif pattern == current_endpoint:
                        return True
            
            # Check children
            if 'children' in item:
                for child in item['children']:
                    if child.get('endpoint') == current_endpoint:
                        return True
        
        return False