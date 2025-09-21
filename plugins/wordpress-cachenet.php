<?php
/**
 * Plugin Name: Cachenet CDN Auto-Purge
 * Plugin URI: https://cachenet.local
 * Description: Automatically purges Cachenet CDN cache when posts/pages are updated
 * Version: 1.0.0
 * Author: Cachenet Team
 * License: GPL v2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: cachenet-cdn
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

class CachenetCDN {
    
    private $api_url;
    private $purge_key;
    private $enabled;
    
    public function __construct() {
        add_action('init', array($this, 'init'));
        add_action('admin_menu', array($this, 'add_admin_menu'));
        add_action('admin_init', array($this, 'admin_init'));
        
        // Hooks for auto-purging
        add_action('save_post', array($this, 'purge_post_cache'), 10, 3);
        add_action('wp_trash_post', array($this, 'purge_post_cache'));
        add_action('wp_untrash_post', array($this, 'purge_post_cache'));
        add_action('delete_post', array($this, 'purge_post_cache'));
        add_action('transition_post_status', array($this, 'purge_post_cache_on_status_change'), 10, 3);
        
        // Comment hooks
        add_action('wp_insert_comment', array($this, 'purge_post_cache_on_comment'), 10, 2);
        add_action('wp_set_comment_status', array($this, 'purge_post_cache_on_comment_status'));
        
        // Theme/plugin hooks
        add_action('switch_theme', array($this, 'purge_all_cache'));
        add_action('activated_plugin', array($this, 'purge_all_cache'));
        add_action('deactivated_plugin', array($this, 'purge_all_cache'));
        
        // Menu hooks
        add_action('wp_update_nav_menu', array($this, 'purge_all_cache'));
        
        // Customizer hooks
        add_action('customize_save_after', array($this, 'purge_all_cache'));
        
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