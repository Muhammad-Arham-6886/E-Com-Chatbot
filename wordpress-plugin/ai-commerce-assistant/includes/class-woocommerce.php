<?php
if (!defined('ABSPATH')) {
    exit;
}

class AI_Commerce_WooCommerce {
    public static function init() {
        add_filter('woocommerce_add_to_cart_redirect', array(__CLASS__, 'handle_cart_redirect'));
        add_action('woocommerce_before_cart', array(__CLASS__, 'render_cart_notice'));
    }

    public static function handle_cart_redirect($url) {
        // If query param 'ai_checkout' is set, redirect directly to checkout page
        if (isset($_GET['ai_checkout']) && $_GET['ai_checkout'] === '1') {
            return wc_get_checkout_url();
        }
        return $url;
    }

    public static function render_cart_notice() {
        if (isset($_GET['ai_added']) && $_GET['ai_added'] === '1') {
            wc_print_notice(__('Item added to cart via AI Shopping Assistant.', 'ai-commerce-assistant'), 'success');
        }
    }
}
