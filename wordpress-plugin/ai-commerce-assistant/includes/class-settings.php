<?php
if (!defined('ABSPATH')) {
    exit;
}

class AI_Commerce_Settings {
    public static function init() {
        add_action('admin_menu', array(__CLASS__, 'add_admin_menu'));
        add_action('admin_init', array(__CLASS__, 'register_settings'));
    }

    public static function add_admin_menu() {
        add_options_page(
            __('AI Commerce Assistant Settings', 'ai-commerce-assistant'),
            __('AI Assistant', 'ai-commerce-assistant'),
            'manage_options',
            'ai-commerce-assistant',
            array(__CLASS__, 'render_settings_page')
        );

        if (class_exists('WooCommerce')) {
            add_submenu_page(
                'woocommerce',
                __('AI Customer & Commerce Assistant', 'ai-commerce-assistant'),
                __('AI Assistant', 'ai-commerce-assistant'),
                'manage_woocommerce',
                'ai-commerce-assistant',
                array(__CLASS__, 'render_settings_page')
            );
        }
    }

    public static function register_settings() {
        register_setting('ai_commerce_settings_group', 'ai_commerce_public_site_id');
        register_setting('ai_commerce_settings_group', 'ai_commerce_api_url');
        register_setting('ai_commerce_settings_group', 'ai_commerce_enabled');
        register_setting('ai_commerce_settings_group', 'ai_commerce_hide_on_admin');
    }

    public static function render_settings_page() {
        if (!current_user_can('manage_options') && !current_user_can('manage_woocommerce')) {
            return;
        }

        $public_site_id = get_option('ai_commerce_public_site_id', '');
        $api_url = get_option('ai_commerce_api_url', 'http://localhost:8000');
        $enabled = get_option('ai_commerce_enabled', 'yes');
        $hide_on_admin = get_option('ai_commerce_hide_on_admin', 'yes');
        ?>
        <div class="wrap">
            <h1><?php echo esc_html(get_admin_page_title()); ?></h1>
            <p><?php esc_html_e('Connect your WordPress and WooCommerce storefront to the local AI Customer & Commerce Assistant SaaS platform.', 'ai-commerce-assistant'); ?></p>
            
            <form action="options.php" method="post" style="background:#fff; padding:24px; border:1px solid #ccd0d4; border-radius:8px; max-width:800px; margin-top:16px;">
                <?php
                settings_fields('ai_commerce_settings_group');
                do_settings_sections('ai_commerce_settings_group');
                ?>

                <table class="form-table">
                    <tr>
                        <th scope="row"><label for="ai_commerce_public_site_id"><?php esc_html_e('Public Site ID', 'ai-commerce-assistant'); ?></label></th>
                        <td>
                            <input type="text" id="ai_commerce_public_site_id" name="ai_commerce_public_site_id" value="<?php echo esc_attr($public_site_id); ?>" class="regular-text code" placeholder="site_xxxxxxxxxxxx" required />
                            <p class="description"><?php esc_html_e('Found in your SaaS Dashboard under Websites -> Installation.', 'ai-commerce-assistant'); ?></p>
                        </td>
                    </tr>

                    <tr>
                        <th scope="row"><label for="ai_commerce_api_url"><?php esc_html_e('SaaS Platform API URL', 'ai-commerce-assistant'); ?></label></th>
                        <td>
                            <input type="url" id="ai_commerce_api_url" name="ai_commerce_api_url" value="<?php echo esc_attr($api_url); ?>" class="regular-text" placeholder="https://app.yourdomain.com" required />
                            <p class="description"><?php esc_html_e('The base URL of your AI Assistant backend server (e.g. http://localhost:8000 or production domain).', 'ai-commerce-assistant'); ?></p>
                        </td>
                    </tr>

                    <tr>
                        <th scope="row"><?php esc_html_e('Enable Chat Widget', 'ai-commerce-assistant'); ?></th>
                        <td>
                            <label for="ai_commerce_enabled">
                                <input type="checkbox" id="ai_commerce_enabled" name="ai_commerce_enabled" value="yes" <?php checked('yes', $enabled); ?> />
                                <?php esc_html_e('Display AI Chat Widget on public storefront pages', 'ai-commerce-assistant'); ?>
                            </label>
                        </td>
                    </tr>

                    <tr>
                        <th scope="row"><?php esc_html_e('Hide for Admin Users', 'ai-commerce-assistant'); ?></th>
                        <td>
                            <label for="ai_commerce_hide_on_admin">
                                <input type="checkbox" id="ai_commerce_hide_on_admin" name="ai_commerce_hide_on_admin" value="yes" <?php checked('yes', $hide_on_admin); ?> />
                                <?php esc_html_e('Hide widget while browsing as Administrator to avoid test clutter', 'ai-commerce-assistant'); ?>
                            </label>
                        </td>
                    </tr>
                </table>

                <?php submit_button(__('Save Settings', 'ai-commerce-assistant')); ?>
            </form>

            <div style="margin-top:24px; padding:16px; background:#f0f6fc; border-left:4px solid #0073aa; max-width:800px;">
                <h3 style="margin-top:0;"><?php esc_html_e('WooCommerce REST API Setup', 'ai-commerce-assistant'); ?></h3>
                <p><?php esc_html_e('To allow the AI Assistant to query live product inventory and generate direct add-to-cart checkouts:', 'ai-commerce-assistant'); ?></p>
                <ol>
                    <li><?php esc_html_e('Go to WooCommerce -> Settings -> Advanced -> REST API.', 'ai-commerce-assistant'); ?></li>
                    <li><?php esc_html_e('Click "Add Key", set Permissions to "Read" (or Read/Write).', 'ai-commerce-assistant'); ?></li>
                    <li><?php esc_html_e('Paste Consumer Key & Secret into the SaaS Integrations tab.', 'ai-commerce-assistant'); ?></li>
                </ol>
            </div>
        </div>
        <?php
    }
}
