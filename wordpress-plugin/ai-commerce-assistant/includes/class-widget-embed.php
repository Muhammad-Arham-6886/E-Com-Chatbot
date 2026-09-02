<?php
if (!defined('ABSPATH')) {
    exit;
}

class AI_Commerce_Widget_Embed {
    public static function init() {
        add_action('wp_footer', array(__CLASS__, 'inject_widget_script'), 9999);
    }

    public static function inject_widget_script() {
        $enabled = get_option('ai_commerce_enabled', 'yes');
        if ($enabled !== 'yes') {
            return;
        }

        $hide_on_admin = get_option('ai_commerce_hide_on_admin', 'yes');
        if ($hide_on_admin === 'yes' && current_user_can('manage_options')) {
            return;
        }

        $public_site_id = get_option('ai_commerce_public_site_id', '');
        if (empty($public_site_id)) {
            return;
        }

        $api_url = rtrim(get_option('ai_commerce_api_url', 'http://localhost:8000'), '/');
        $script_src = esc_url($api_url . '/static/widget.js');
        $site_id_attr = esc_attr($public_site_id);
        $api_url_attr = esc_attr($api_url);

        ?>
        <!-- AI Customer & Commerce Assistant Widget -->
        <script 
            src="<?php echo $script_src; ?>" 
            data-site-id="<?php echo $site_id_attr; ?>" 
            data-api-url="<?php echo $api_url_attr; ?>" 
            async>
        </script>
        <!-- /AI Customer & Commerce Assistant Widget -->
        <?php
    }
}
