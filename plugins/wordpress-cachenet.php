<?php
/**
 * Plugin Name: Cachenet CDN
 * Plugin URI: https://cachenet.enterprise
 * Description: Automatically purge Cachenet CDN cache when content is updated. Enterprise-grade CDN integration for WordPress.
 * Version: 1.2.0
 * Author: Cachenet Enterprise
 * Author URI: https://cachenet.enterprise
 * License: GPL v2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: cachenet-cdn
 * Domain Path: /languages
 * Requires at least: 5.0
 * Tested up to: 6.3
 * Requires PHP: 7.4
 * Network: true
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Plugin constants
define('CACHENET_PLUGIN_VERSION', '1.2.0');
define('CACHENET_PLUGIN_URL', plugin_dir_url(__FILE__));
define('CACHENET_PLUGIN_PATH', plugin_dir_path(__FILE__));

/**
 * Main Cachenet CDN Plugin Class
 */
class CachenetCDN {
    
    private $api_url;
    private $api_token;
    private $domain_id;
    private $purge_key;
    
    public function __construct() {
        add_action('init', array($this, 'init'));
    }
    
    /**
     * Initialize the plugin
     */
    public function init() {
        // Load plugin settings
        $this->load_settings();
        
        // Add admin hooks
        if (is_admin()) {
            add_action('admin_menu', array($this, 'add_admin_menu'));
            add_action('admin_init', array($this, 'register_settings'));
            add_action('wp_ajax_cachenet_test_connection', array($this, 'test_connection'));
            add_action('wp_ajax_cachenet_purge_all', array($this, 'purge_all_cache'));
        }
        
        // Content update hooks
        add_action('save_post', array($this, 'on_post_save'), 10, 3);
        add_action('wp_trash_post', array($this, 'on_post_delete'));
        add_action('wp_update_nav_menu', array($this, 'on_menu_update'));
        add_action('customize_save_after', array($this, 'on_customizer_save'));
        add_action('switch_theme', array($this, 'on_theme_change'));
        
        // Comment hooks
        add_action('comment_post', array($this, 'on_comment_post'));
        add_action('wp_set_comment_status', array($this, 'on_comment_status_change'));
        
        // Add toolbar menu
        add_action('admin_bar_menu', array($this, 'add_toolbar_menu'), 999);
        
        // Load text domain
        add_action('plugins_loaded', array($this, 'load_textdomain'));
    }
    
    private function load_settings() {
        $this->api_url = get_option('cachenet_api_url', '');
        $this->api_token = get_option('cachenet_api_token', '');
        $this->domain_id = get_option('cachenet_domain_id', '');
        $this->purge_key = get_option('cachenet_purge_key', '');
    }
    
    public function add_admin_menu() {
        add_options_page(
            __('Cachenet CDN Settings', 'cachenet-cdn'),
            __('Cachenet CDN', 'cachenet-cdn'),
            'manage_options',
            'cachenet-cdn',
            array($this, 'admin_page')
        );
    }
    
    public function register_settings() {
        register_setting('cachenet_cdn_settings', 'cachenet_api_url');
        register_setting('cachenet_cdn_settings', 'cachenet_api_token');
        register_setting('cachenet_cdn_settings', 'cachenet_domain_id');
        register_setting('cachenet_cdn_settings', 'cachenet_purge_key');
        register_setting('cachenet_cdn_settings', 'cachenet_auto_purge');
        register_setting('cachenet_cdn_settings', 'cachenet_purge_posts');
        register_setting('cachenet_cdn_settings', 'cachenet_purge_pages');
        register_setting('cachenet_cdn_settings', 'cachenet_purge_archives');
        register_setting('cachenet_cdn_settings', 'cachenet_purge_feeds');
        register_setting('cachenet_cdn_settings', 'cachenet_debug_mode');
    }
    
    public function admin_page() {
        ?>
        <div class="wrap">
            <h1><?php _e('Cachenet CDN Settings', 'cachenet-cdn'); ?></h1>
            
            <div class="cachenet-header">
                <h2>🚀 Cachenet Enterprise CDN</h2>
                <p><?php _e('Configure your Cachenet Enterprise CDN settings below. This plugin automatically purges your CDN cache when content is updated.', 'cachenet-cdn'); ?></p>
            </div>
            
            <form method="post" action="options.php">
                <?php settings_fields('cachenet_cdn_settings'); ?>
                <?php do_settings_sections('cachenet_cdn_settings'); ?>
                
                <table class="form-table">
                    <tr>
                        <th scope="row"><?php _e('API URL', 'cachenet-cdn'); ?></th>
                        <td>
                            <input type="url" 
                                   name="cachenet_api_url" 
                                   value="<?php echo esc_attr($this->api_url); ?>" 
                                   class="regular-text" 
                                   placeholder="https://api.cachenet.enterprise" />
                            <p class="description"><?php _e('Your Cachenet API endpoint URL.', 'cachenet-cdn'); ?></p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row"><?php _e('API Token', 'cachenet-cdn'); ?></th>
                        <td>
                            <input type="password" 
                                   name="cachenet_api_token" 
                                   value="<?php echo esc_attr($this->api_token); ?>" 
                                   class="regular-text" />
                            <p class="description"><?php _e('Your Cachenet API authentication token from the admin dashboard.', 'cachenet-cdn'); ?></p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row"><?php _e('Domain ID', 'cachenet-cdn'); ?></th>
                        <td>
                            <input type="number" 
                                   name="cachenet_domain_id" 
                                   value="<?php echo esc_attr($this->domain_id); ?>" 
                                   class="small-text" />
                            <p class="description"><?php _e('Your domain ID in the Cachenet system.', 'cachenet-cdn'); ?></p>
                        </td>
                    </tr>
                </table>
                
                <h2><?php _e('Auto-Purge Settings', 'cachenet-cdn'); ?></h2>
                
                <table class="form-table">
                    <tr>
                        <th scope="row"><?php _e('Enable Auto-Purge', 'cachenet-cdn'); ?></th>
                        <td>
                            <label>
                                <input type="checkbox" 
                                       name="cachenet_auto_purge" 
                                       value="1" 
                                       <?php checked(get_option('cachenet_auto_purge', 1)); ?> />
                                <?php _e('Automatically purge cache when content is updated', 'cachenet-cdn'); ?>
                            </label>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row"><?php _e('Debug Mode', 'cachenet-cdn'); ?></th>
                        <td>
                            <label>
                                <input type="checkbox" 
                                       name="cachenet_debug_mode" 
                                       value="1" 
                                       <?php checked(get_option('cachenet_debug_mode', 0)); ?> />
                                <?php _e('Enable debug logging for troubleshooting', 'cachenet-cdn'); ?>
                            </label>
                        </td>
                    </tr>
                </table>
                
                <div class="cachenet-actions">
                    <?php submit_button(__('Save Settings', 'cachenet-cdn'), 'primary', 'submit', false); ?>
                    <button type="button" id="test-connection" class="button button-secondary">
                        <?php _e('Test Connection', 'cachenet-cdn'); ?>
                    </button>
                    <button type="button" id="purge-all" class="button button-secondary">
                        <?php _e('Purge All Cache', 'cachenet-cdn'); ?>
                    </button>
                </div>
                
                <div id="cachenet-status" class="cachenet-status"></div>
            </form>
        </div>
        
        <style>
        .cachenet-header {
            background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            text-align: center;
        }
        .cachenet-header h2 {
            margin: 0 0 10px;
            font-size: 28px;
        }
        .cachenet-actions {
            margin: 20px 0;
        }
        .cachenet-actions .button {
            margin-right: 10px;
        }
        .cachenet-status {
            margin: 15px 0;
            padding: 12px 16px;
            border-radius: 6px;
            display: none;
            font-weight: 500;
        }
        .cachenet-status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .cachenet-status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        </style>
        
        <script>
        jQuery(document).ready(function($) {
            $('#test-connection').on('click', function() {
                var button = $(this);
                var status = $('#cachenet-status');
                
                button.prop('disabled', true).text('<?php _e('Testing...', 'cachenet-cdn'); ?>');
                
                $.post(ajaxurl, {
                    action: 'cachenet_test_connection',
                    nonce: '<?php echo wp_create_nonce('cachenet_nonce'); ?>'
                }, function(response) {
                    if (response.success) {
                        status.removeClass('error').addClass('success').text('✅ <?php _e('Connection successful! Your Cachenet CDN is ready.', 'cachenet-cdn'); ?>').show();
                    } else {
                        status.removeClass('success').addClass('error').text('❌ <?php _e('Connection failed. Please check your API settings.', 'cachenet-cdn'); ?>').show();
                    }
                }).always(function() {
                    button.prop('disabled', false).text('<?php _e('Test Connection', 'cachenet-cdn'); ?>');
                });
            });
            
            $('#purge-all').on('click', function() {
                var button = $(this);
                var status = $('#cachenet-status');
                
                if (!confirm('<?php _e('Are you sure you want to purge all cache?', 'cachenet-cdn'); ?>')) {
                    return;
                }
                
                button.prop('disabled', true).text('<?php _e('Purging...', 'cachenet-cdn'); ?>');
                
                $.post(ajaxurl, {
                    action: 'cachenet_purge_all',
                    nonce: '<?php echo wp_create_nonce('cachenet_nonce'); ?>'
                }, function(response) {
                    if (response.success) {
                        status.removeClass('error').addClass('success').text('🚀 <?php _e('Cache purged successfully!', 'cachenet-cdn'); ?>').show();
                    } else {
                        status.removeClass('success').addClass('error').text('❌ <?php _e('Cache purge failed. Please try again.', 'cachenet-cdn'); ?>').show();
                    }
                }).always(function() {
                    button.prop('disabled', false).text('<?php _e('Purge All Cache', 'cachenet-cdn'); ?>');
                });
            });
        });
        </script>
        <?php
    }
    
    public function test_connection() {
        check_ajax_referer('cachenet_nonce', 'nonce');
        
        if (!current_user_can('manage_options')) {
            wp_die(__('Insufficient permissions', 'cachenet-cdn'));
        }
        
        $response = $this->make_api_request('/health', 'GET');
        
        if ($response && !is_wp_error($response) && wp_remote_retrieve_response_code($response) === 200) {
            wp_send_json_success();
        } else {
            wp_send_json_error();
        }
    }
    
    public function purge_all_cache() {
        check_ajax_referer('cachenet_nonce', 'nonce');
        
        if (!current_user_can('manage_options')) {
            wp_die(__('Insufficient permissions', 'cachenet-cdn'));
        }
        
        $result = $this->purge_cache();
        
        if ($result) {
            wp_send_json_success();
        } else {
            wp_send_json_error();
        }
    }
    
    public function on_post_save($post_id, $post, $update) {
        if (!get_option('cachenet_auto_purge', 1)) {
            return;
        }
        
        // Skip auto-saves and revisions
        if (wp_is_post_autosave($post_id) || wp_is_post_revision($post_id)) {
            return;
        }
        
        // Only purge for published posts
        if ($post->post_status !== 'publish') {
            return;
        }
        
        $this->purge_post_cache($post_id);
    }
    
    public function on_post_delete($post_id) {
        if (!get_option('cachenet_auto_purge', 1)) {
            return;
        }
        
        $this->purge_post_cache($post_id);
    }
    
    public function on_menu_update() {
        if (!get_option('cachenet_auto_purge', 1)) {
            return;
        }
        
        $this->purge_cache();
    }
    
    public function on_customizer_save() {
        if (!get_option('cachenet_auto_purge', 1)) {
            return;
        }
        
        $this->purge_cache();
    }
    
    public function on_theme_change() {
        if (!get_option('cachenet_auto_purge', 1)) {
            return;
        }
        
        $this->purge_cache();
    }
    
    public function on_comment_post($comment_id) {
        if (!get_option('cachenet_auto_purge', 1)) {
            return;
        }
        
        $comment = get_comment($comment_id);
        if ($comment) {
            $this->purge_post_cache($comment->comment_post_ID);
        }
    }
    
    public function on_comment_status_change($comment_id) {
        if (!get_option('cachenet_auto_purge', 1)) {
            return;
        }
        
        $comment = get_comment($comment_id);
        if ($comment) {
            $this->purge_post_cache($comment->comment_post_ID);
        }
    }
    
    private function purge_post_cache($post_id) {
        $post = get_post($post_id);
        if (!$post) {
            return false;
        }
        
        $urls = array();
        
        // Post URL
        $urls[] = get_permalink($post_id);
        
        // Home page
        $urls[] = home_url('/');
        
        return $this->purge_urls($urls);
    }
    
    private function purge_cache() {
        if (empty($this->domain_id)) {
            $this->log('Domain ID not configured');
            return false;
        }
        
        $response = $this->make_api_request('/cache/purge/domain', 'POST', array(
            'domain_id' => intval($this->domain_id)
        ));
        
        if (is_wp_error($response)) {
            $this->log('Cache purge failed: ' . $response->get_error_message());
            return false;
        }
        
        $this->log('All cache purged successfully');
        return true;
    }
    
    private function purge_urls($urls) {
        if (empty($urls) || empty($this->domain_id)) {
            return false;
        }
        
        $success = true;
        
        foreach ($urls as $url) {
            $path = parse_url($url, PHP_URL_PATH);
            if (empty($path)) {
                $path = '/';
            }
            
            $response = $this->make_api_request('/cache/purge/url', 'POST', array(
                'domain_id' => intval($this->domain_id),
                'url_path' => $path
            ));
            
            if (is_wp_error($response)) {
                $this->log('URL purge failed for ' . $url . ': ' . $response->get_error_message());
                $success = false;
            } else {
                $this->log('Cache purged for: ' . $url);
            }
        }
        
        return $success;
    }
    
    private function make_api_request($endpoint, $method = 'GET', $data = null) {
        if (empty($this->api_url) || empty($this->api_token)) {
            return new WP_Error('missing_config', 'API URL and token are required');
        }
        
        $url = rtrim($this->api_url, '/') . '/api' . $endpoint;
        
        $args = array(
            'method' => $method,
            'headers' => array(
                'Authorization' => 'Bearer ' . $this->api_token,
                'Content-Type' => 'application/json',
                'User-Agent' => 'WordPress-Cachenet/' . CACHENET_PLUGIN_VERSION
            ),
            'timeout' => 30
        );
        
        if ($data && ($method === 'POST' || $method === 'PUT')) {
            $args['body'] = json_encode($data);
        }
        
        return wp_remote_request($url, $args);
    }
    
    public function add_toolbar_menu($wp_admin_bar) {
        if (!current_user_can('manage_options')) {
            return;
        }
        
        $wp_admin_bar->add_node(array(
            'id' => 'cachenet-cdn',
            'title' => '<span class="ab-icon dashicons-performance"></span>' . __('Cachenet', 'cachenet-cdn'),
            'href' => admin_url('options-general.php?page=cachenet-cdn')
        ));
        
        $wp_admin_bar->add_node(array(
            'id' => 'cachenet-purge-all',
            'parent' => 'cachenet-cdn',
            'title' => __('Purge All Cache', 'cachenet-cdn'),
            'href' => '#',
            'meta' => array('onclick' => 'return confirm("Are you sure?");')
        ));
    }
    
    private function log($message) {
        if (get_option('cachenet_debug_mode', 0)) {
            error_log('[Cachenet CDN] ' . $message);
        }
    }
    
    public function load_textdomain() {
        load_plugin_textdomain('cachenet-cdn', false, dirname(plugin_basename(__FILE__)) . '/languages');
    }
}

// Initialize the plugin
new CachenetCDN();
?>
        
        // Widget hooks
        add_action('sidebar_admin_setup', array($this, 'purge_all_cache'));
        
        // Admin bar purge button
        add_action('admin_bar_menu', array($this, 'add_admin_bar_button'), 100);
        add_action('wp_ajax_cachenet_purge_all', array($this, 'ajax_purge_all'));
        add_action('wp_ajax_cachenet_purge_current', array($this, 'ajax_purge_current'));
    }
    
    public function init() {
        $this->api_url = get_option('cachenet_api_url', '');
        $this->purge_key = get_option('cachenet_purge_key', '');
        $this->enabled = get_option('cachenet_enabled', false);
        
        // Load plugin textdomain
        load_plugin_textdomain('cachenet-cdn', false, dirname(plugin_basename(__FILE__)) . '/languages');
    }
    
    public function add_admin_menu() {
        add_options_page(
            __('Cachenet CDN Settings', 'cachenet-cdn'),
            __('Cachenet CDN', 'cachenet-cdn'),
            'manage_options',
            'cachenet-cdn',
            array($this, 'admin_page')
        );
    }
    
    public function admin_init() {
        register_setting('cachenet_settings', 'cachenet_api_url');
        register_setting('cachenet_settings', 'cachenet_purge_key');
        register_setting('cachenet_settings', 'cachenet_enabled');
        register_setting('cachenet_settings', 'cachenet_auto_purge_posts');
        register_setting('cachenet_settings', 'cachenet_auto_purge_pages');
        register_setting('cachenet_settings', 'cachenet_auto_purge_home');
        register_setting('cachenet_settings', 'cachenet_debug_mode');
        
        add_settings_section(
            'cachenet_main_section',
            __('Main Settings', 'cachenet-cdn'),
            array($this, 'settings_section_callback'),
            'cachenet_settings'
        );
        
        add_settings_field(
            'cachenet_api_url',
            __('Cachenet API URL', 'cachenet-cdn'),
            array($this, 'api_url_callback'),
            'cachenet_settings',
            'cachenet_main_section'
        );
        
        add_settings_field(
            'cachenet_purge_key',
            __('Purge Key', 'cachenet-cdn'),
            array($this, 'purge_key_callback'),
            'cachenet_settings',
            'cachenet_main_section'
        );
        
        add_settings_field(
            'cachenet_enabled',
            __('Enable Auto-Purge', 'cachenet-cdn'),
            array($this, 'enabled_callback'),
            'cachenet_settings',
            'cachenet_main_section'
        );
        
        add_settings_field(
            'cachenet_auto_purge_posts',
            __('Auto-purge Posts', 'cachenet-cdn'),
            array($this, 'auto_purge_posts_callback'),
            'cachenet_settings',
            'cachenet_main_section'
        );
        
        add_settings_field(
            'cachenet_auto_purge_pages',
            __('Auto-purge Pages', 'cachenet-cdn'),
            array($this, 'auto_purge_pages_callback'),
            'cachenet_settings',
            'cachenet_main_section'
        );
        
        add_settings_field(
            'cachenet_auto_purge_home',
            __('Auto-purge Homepage', 'cachenet-cdn'),
            array($this, 'auto_purge_home_callback'),
            'cachenet_settings',
            'cachenet_main_section'
        );
        
        add_settings_field(
            'cachenet_debug_mode',
            __('Debug Mode', 'cachenet-cdn'),
            array($this, 'debug_mode_callback'),
            'cachenet_settings',
            'cachenet_main_section'
        );
    }
    
    public function admin_page() {
        ?>
        <div class="wrap">
            <h1><?php echo esc_html(get_admin_page_title()); ?></h1>
            <form action="options.php" method="post">
                <?php
                settings_fields('cachenet_settings');
                do_settings_sections('cachenet_settings');
                submit_button();
                ?>
            </form>
            
            <div class="cachenet-actions">
                <h2><?php _e('Manual Cache Control', 'cachenet-cdn'); ?></h2>
                <p><?php _e('Use these buttons to manually purge cache when needed.', 'cachenet-cdn'); ?></p>
                
                <button type="button" id="purge-all-cache" class="button button-primary">
                    <?php _e('Purge All Cache', 'cachenet-cdn'); ?>
                </button>
                
                <button type="button" id="purge-current-page" class="button button-secondary">
                    <?php _e('Purge Current Page', 'cachenet-cdn'); ?>
                </button>
                
                <div id="purge-result" style="margin-top: 10px;"></div>
            </div>
            
            <script type="text/javascript">
            jQuery(document).ready(function($) {
                $('#purge-all-cache').click(function() {
                    var button = $(this);
                    button.prop('disabled', true).text('<?php _e('Purging...', 'cachenet-cdn'); ?>');
                    
                    $.post(ajaxurl, {
                        action: 'cachenet_purge_all',
                        nonce: '<?php echo wp_create_nonce('cachenet_purge_all'); ?>'
                    }, function(response) {
                        $('#purge-result').html('<div class="notice notice-' + (response.success ? 'success' : 'error') + '"><p>' + response.data + '</p></div>');
                        button.prop('disabled', false).text('<?php _e('Purge All Cache', 'cachenet-cdn'); ?>');
                    });
                });
                
                $('#purge-current-page').click(function() {
                    var button = $(this);
                    button.prop('disabled', true).text('<?php _e('Purging...', 'cachenet-cdn'); ?>');
                    
                    $.post(ajaxurl, {
                        action: 'cachenet_purge_current',
                        url: window.location.href,
                        nonce: '<?php echo wp_create_nonce('cachenet_purge_current'); ?>'
                    }, function(response) {
                        $('#purge-result').html('<div class="notice notice-' + (response.success ? 'success' : 'error') + '"><p>' + response.data + '</p></div>');
                        button.prop('disabled', false).text('<?php _e('Purge Current Page', 'cachenet-cdn'); ?>');
                    });
                });
            });
            </script>
        </div>
        <?php
    }
    
    public function settings_section_callback() {
        echo '<p>' . __('Configure your Cachenet CDN settings below. You can find your API URL and Purge Key in your Cachenet client dashboard.', 'cachenet-cdn') . '</p>';
    }
    
    public function api_url_callback() {
        $value = get_option('cachenet_api_url', '');
        echo '<input type="url" name="cachenet_api_url" value="' . esc_attr($value) . '" class="regular-text" placeholder="https://api.cachenet.local" />';
        echo '<p class="description">' . __('Your Cachenet API URL (e.g., https://api.cachenet.local)', 'cachenet-cdn') . '</p>';
    }
    
    public function purge_key_callback() {
        $value = get_option('cachenet_purge_key', '');
        echo '<input type="text" name="cachenet_purge_key" value="' . esc_attr($value) . '" class="regular-text" />';
        echo '<p class="description">' . __('Your domain-specific purge key from Cachenet dashboard', 'cachenet-cdn') . '</p>';
    }
    
    public function enabled_callback() {
        $value = get_option('cachenet_enabled', false);
        echo '<label><input type="checkbox" name="cachenet_enabled" value="1"' . checked(1, $value, false) . ' /> ' . __('Enable automatic cache purging', 'cachenet-cdn') . '</label>';
    }
    
    public function auto_purge_posts_callback() {
        $value = get_option('cachenet_auto_purge_posts', true);
        echo '<label><input type="checkbox" name="cachenet_auto_purge_posts" value="1"' . checked(1, $value, false) . ' /> ' . __('Automatically purge cache when posts are updated', 'cachenet-cdn') . '</label>';
    }
    
    public function auto_purge_pages_callback() {
        $value = get_option('cachenet_auto_purge_pages', true);
        echo '<label><input type="checkbox" name="cachenet_auto_purge_pages" value="1"' . checked(1, $value, false) . ' /> ' . __('Automatically purge cache when pages are updated', 'cachenet-cdn') . '</label>';
    }
    
    public function auto_purge_home_callback() {
        $value = get_option('cachenet_auto_purge_home', true);
        echo '<label><input type="checkbox" name="cachenet_auto_purge_home" value="1"' . checked(1, $value, false) . ' /> ' . __('Automatically purge homepage when content is updated', 'cachenet-cdn') . '</label>';
    }
    
    public function debug_mode_callback() {
        $value = get_option('cachenet_debug_mode', false);
        echo '<label><input type="checkbox" name="cachenet_debug_mode" value="1"' . checked(1, $value, false) . ' /> ' . __('Enable debug logging', 'cachenet-cdn') . '</label>';
        echo '<p class="description">' . __('Debug logs will be written to your WordPress debug log', 'cachenet-cdn') . '</p>';
    }
    
    public function add_admin_bar_button($wp_admin_bar) {
        if (!current_user_can('manage_options') || !$this->enabled) {
            return;
        }
        
        $wp_admin_bar->add_node(array(
            'id' => 'cachenet-purge',
            'title' => __('Purge Cache', 'cachenet-cdn'),
            'href' => '#',
            'meta' => array(
                'onclick' => 'cachenetPurgeCurrentPage(); return false;'
            )
        ));
        
        // Add JavaScript for admin bar button
        add_action('wp_footer', array($this, 'admin_bar_script'));
        add_action('admin_footer', array($this, 'admin_bar_script'));
    }
    
    public function admin_bar_script() {
        ?>
        <script type="text/javascript">
        function cachenetPurgeCurrentPage() {
            if (confirm('<?php _e('Are you sure you want to purge the cache for this page?', 'cachenet-cdn'); ?>')) {
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '<?php echo admin_url('admin-ajax.php'); ?>');
                xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                xhr.onload = function() {
                    if (xhr.status === 200) {
                        var response = JSON.parse(xhr.responseText);
                        alert(response.data);
                        if (response.success) {
                            location.reload();
                        }
                    } else {
                        alert('<?php _e('Error purging cache', 'cachenet-cdn'); ?>');
                    }
                };
                xhr.send('action=cachenet_purge_current&url=' + encodeURIComponent(window.location.href) + '&nonce=<?php echo wp_create_nonce('cachenet_purge_current'); ?>');
            }
        }
        </script>
        <?php
    }
    
    public function purge_post_cache($post_id, $post = null, $update = null) {
        if (!$this->enabled || !$this->purge_key) {
            return;
        }
        
        if (defined('DOING_AUTOSAVE') && DOING_AUTOSAVE) {
            return;
        }
        
        if (!$post) {
            $post = get_post($post_id);
        }
        
        if (!$post || $post->post_status !== 'publish') {
            return;
        }
        
        // Check if auto-purge is enabled for this post type
        if ($post->post_type === 'post' && !get_option('cachenet_auto_purge_posts', true)) {
            return;
        }
        
        if ($post->post_type === 'page' && !get_option('cachenet_auto_purge_pages', true)) {
            return;
        }
        
        $post_url = get_permalink($post_id);
        $this->purge_url($post_url);
        
        // Also purge homepage if enabled
        if (get_option('cachenet_auto_purge_home', true)) {
            $this->purge_url(home_url('/'));
        }
        
        // Purge category and tag pages
        $categories = get_the_category($post_id);
        foreach ($categories as $category) {
            $this->purge_url(get_category_link($category->term_id));
        }
        
        $tags = get_the_tags($post_id);
        if ($tags) {
            foreach ($tags as $tag) {
                $this->purge_url(get_tag_link($tag->term_id));
            }
        }
        
        $this->debug_log("Cache purged for post: {$post->post_title} ({$post_url})");
    }
    
    public function purge_post_cache_on_status_change($new_status, $old_status, $post) {
        if ($new_status === 'publish' || $old_status === 'publish') {
            $this->purge_post_cache($post->ID, $post);
        }
    }
    
    public function purge_post_cache_on_comment($comment_id, $comment) {
        if (!$this->enabled || !$this->purge_key) {
            return;
        }
        
        $post_id = $comment->comment_post_ID;
        $this->purge_post_cache($post_id);
    }
    
    public function purge_post_cache_on_comment_status($comment_id) {
        if (!$this->enabled || !$this->purge_key) {
            return;
        }
        
        $comment = get_comment($comment_id);
        if ($comment) {
            $this->purge_post_cache($comment->comment_post_ID);
        }
    }
    
    public function purge_all_cache() {
        if (!$this->enabled || !$this->purge_key) {
            return;
        }
        
        $response = wp_remote_post($this->api_url . '/purge', array(
            'body' => json_encode(array(
                'purge_key' => $this->purge_key,
                'url_path' => '*'
            )),
            'headers' => array(
                'Content-Type' => 'application/json'
            ),
            'timeout' => 30
        ));
        
        if (is_wp_error($response)) {
            $this->debug_log("Error purging all cache: " . $response->get_error_message());
            return false;
        }
        
        $this->debug_log("All cache purged successfully");
        return true;
    }
    
    public function purge_url($url) {
        if (!$this->enabled || !$this->purge_key) {
            return false;
        }
        
        $parsed_url = parse_url($url);
        $url_path = $parsed_url['path'] ?? '/';
        
        $response = wp_remote_post($this->api_url . '/purge', array(
            'body' => json_encode(array(
                'purge_key' => $this->purge_key,
                'url_path' => $url_path
            )),
            'headers' => array(
                'Content-Type' => 'application/json'
            ),
            'timeout' => 30
        ));
        
        if (is_wp_error($response)) {
            $this->debug_log("Error purging URL {$url}: " . $response->get_error_message());
            return false;
        }
        
        $this->debug_log("Cache purged for URL: {$url}");
        return true;
    }
    
    public function ajax_purge_all() {
        check_ajax_referer('cachenet_purge_all', 'nonce');
        
        if (!current_user_can('manage_options')) {
            wp_die(__('Insufficient permissions', 'cachenet-cdn'));
        }
        
        $result = $this->purge_all_cache();
        
        if ($result) {
            wp_send_json_success(__('All cache purged successfully!', 'cachenet-cdn'));
        } else {
            wp_send_json_error(__('Error purging cache. Please check your settings.', 'cachenet-cdn'));
        }
    }
    
    public function ajax_purge_current() {
        check_ajax_referer('cachenet_purge_current', 'nonce');
        
        if (!current_user_can('manage_options')) {
            wp_die(__('Insufficient permissions', 'cachenet-cdn'));
        }
        
        $url = sanitize_url($_POST['url']);
        $result = $this->purge_url($url);
        
        if ($result) {
            wp_send_json_success(__('Page cache purged successfully!', 'cachenet-cdn'));
        } else {
            wp_send_json_error(__('Error purging page cache. Please check your settings.', 'cachenet-cdn'));
        }
    }
    
    private function debug_log($message) {
        if (get_option('cachenet_debug_mode', false) && defined('WP_DEBUG') && WP_DEBUG) {
            error_log("[Cachenet CDN] " . $message);
        }
    }
}

// Initialize the plugin
new CachenetCDN();

// Activation hook
register_activation_hook(__FILE__, function() {
    add_option('cachenet_enabled', false);
    add_option('cachenet_auto_purge_posts', true);
    add_option('cachenet_auto_purge_pages', true);
    add_option('cachenet_auto_purge_home', true);
    add_option('cachenet_debug_mode', false);
});

// Deactivation hook
register_deactivation_hook(__FILE__, function() {
    // Clean up if needed
});
?>