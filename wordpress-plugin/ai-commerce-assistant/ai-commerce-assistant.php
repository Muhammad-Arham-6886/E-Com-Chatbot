<?php
/**
 * Plugin Name: AI Customer & Commerce Assistant
 * Plugin URI: https://github.com/ai-commerce-assistant
 * Description: Embed an intelligent, local AI-powered chatbot and WooCommerce sales assistant on your website.
 * Version: 1.0.0
 * Author: AI Customer & Commerce Assistant Team
 * Author URI: https://ai-commerce-assistant.com
 * License: GPLv2 or later
 * Text Domain: ai-commerce-assistant
 */

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

define('AI_COMMERCE_VERSION', '1.0.0');
define('AI_COMMERCE_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('AI_COMMERCE_PLUGIN_URL', plugin_dir_url(__FILE__));

// Autoload includes
require_once AI_COMMERCE_PLUGIN_DIR . 'includes/class-settings.php';
require_once AI_COMMERCE_PLUGIN_DIR . 'includes/class-widget-embed.php';
require_once AI_COMMERCE_PLUGIN_DIR . 'includes/class-woocommerce.php';

class AI_Commerce_Assistant {
    private static $instance = null;

    public static function get_instance() {
        if (null === self::$instance) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        // Initialize settings page
        AI_Commerce_Settings::init();
        
        // Initialize widget embed
        AI_Commerce_Widget_Embed::init();

        // Initialize WooCommerce features if WooCommerce is active
        if (class_exists('WooCommerce')) {
            AI_Commerce_WooCommerce::init();
        }

        add_action('init', array($this, 'load_textdomain'));
    }

    public function load_textdomain() {
        load_plugin_textdomain('ai-commerce-assistant', false, dirname(plugin_basename(__FILE__)) . '/languages');
    }
}

// Instantiate plugin
add_action('plugins_loaded', array('AI_Commerce_Assistant', 'get_instance'));

// Activation Hook: Set defaults
register_activation_hook(__FILE__, function() {
    if (!get_option('ai_commerce_api_url')) {
        update_option('ai_commerce_api_url', 'http://localhost:8000');
    }
    if (!get_option('ai_commerce_enabled')) {
        update_option('ai_commerce_enabled', 'yes');
    }
});
