# shared/utils/template_helpers.py
from flask import current_app
from shared.navigation_config import NavigationConfig

def register_template_helpers(app):
    """Register template context processors and filters"""
    
    @app.context_processor
    def inject_navigation():
        """Inject navigation data into all templates"""
        return {
            'NavigationConfig': NavigationConfig,
            'get_navigation_items': NavigationConfig.get_navigation_items,
            'get_current_nav_item': NavigationConfig.get_current_nav_item,
            'get_breadcrumbs': NavigationConfig.get_breadcrumbs,
            'should_expand_section': NavigationConfig.should_expand_section
        }
    
    @app.template_filter('active_if')
    def active_if(condition):
        """Template filter to return 'active' class if condition is true"""
        return 'active' if condition else ''
    
    @app.template_filter('expanded_if')
    def expanded_if(condition):
        """Template filter to return 'expanded' class if condition is true"""
        return 'expanded' if condition else ''