<?php
/**
 * English Language File for Cachenet CDN WHMCS Module
 */

$_LANG['cachenet']['title'] = 'Cachenet CDN';
$_LANG['cachenet']['description'] = 'High-performance Content Delivery Network';

// Client Area
$_LANG['cachenet']['clientarea']['title'] = 'CDN Management';
$_LANG['cachenet']['clientarea']['status'] = 'CDN Status';
$_LANG['cachenet']['clientarea']['enabled'] = 'Enabled';
$_LANG['cachenet']['clientarea']['disabled'] = 'Disabled';
$_LANG['cachenet']['clientarea']['origin_ip'] = 'Origin Server IP';
$_LANG['cachenet']['clientarea']['cname_target'] = 'CNAME Target';
$_LANG['cachenet']['clientarea']['ssl_status'] = 'SSL Certificate';
$_LANG['cachenet']['clientarea']['ssl_active'] = 'Active';
$_LANG['cachenet']['clientarea']['ssl_pending'] = 'Pending';
$_LANG['cachenet']['clientarea']['ssl_error'] = 'Error';
$_LANG['cachenet']['clientarea']['bandwidth_usage'] = 'Bandwidth Usage';
$_LANG['cachenet']['clientarea']['bandwidth_limit'] = 'Bandwidth Limit';
$_LANG['cachenet']['clientarea']['cache_hit_ratio'] = 'Cache Hit Ratio';
$_LANG['cachenet']['clientarea']['regions'] = 'Edge Regions';
$_LANG['cachenet']['clientarea']['purge_cache'] = 'Purge Cache';
$_LANG['cachenet']['clientarea']['toggle_cdn'] = 'Toggle CDN';
$_LANG['cachenet']['clientarea']['download_ssl'] = 'Download SSL Certificate';
$_LANG['cachenet']['clientarea']['configure_origin'] = 'Configure Origin Server';

// Buttons
$_LANG['cachenet']['buttons']['enable'] = 'Enable CDN';
$_LANG['cachenet']['buttons']['disable'] = 'Disable CDN';
$_LANG['cachenet']['buttons']['purge'] = 'Purge Cache';
$_LANG['cachenet']['buttons']['renew_ssl'] = 'Renew SSL';
$_LANG['cachenet']['buttons']['save'] = 'Save Configuration';

// Messages
$_LANG['cachenet']['messages']['cdn_enabled'] = 'CDN has been successfully enabled for your domain.';
$_LANG['cachenet']['messages']['cdn_disabled'] = 'CDN has been successfully disabled for your domain.';
$_LANG['cachenet']['messages']['cache_purged'] = 'Cache has been successfully purged.';
$_LANG['cachenet']['messages']['ssl_renewed'] = 'SSL certificate renewal has been initiated.';
$_LANG['cachenet']['messages']['config_saved'] = 'Configuration has been saved successfully.';
$_LANG['cachenet']['messages']['error'] = 'An error occurred. Please try again or contact support.';

// Help Text
$_LANG['cachenet']['help']['origin_ip'] = 'Enter the IP address of your origin server (where your website is hosted).';
$_LANG['cachenet']['help']['cname'] = 'Point your domain\'s DNS to this CNAME target to enable the CDN.';
$_LANG['cachenet']['help']['ssl'] = 'SSL certificates are automatically issued and renewed for your domain.';
$_LANG['cachenet']['help']['cache_purge'] = 'Use this to clear all cached content and force a fresh reload from your origin server.';
$_LANG['cachenet']['help']['bandwidth'] = 'Monitor your monthly bandwidth usage and limits.';

// Errors
$_LANG['cachenet']['errors']['invalid_ip'] = 'Please enter a valid IP address for your origin server.';
$_LANG['cachenet']['errors']['api_error'] = 'Unable to connect to Cachenet API. Please try again later.';
$_LANG['cachenet']['errors']['permission_denied'] = 'You do not have permission to perform this action.';
$_LANG['cachenet']['errors']['domain_not_found'] = 'Domain not found in CDN configuration.';
$_LANG['cachenet']['errors']['ssl_error'] = 'SSL certificate could not be issued. Please check your DNS configuration.';

// Admin Area
$_LANG['cachenet']['admin']['title'] = 'Cachenet CDN Administration';
$_LANG['cachenet']['admin']['test_connection'] = 'Test API Connection';
$_LANG['cachenet']['admin']['connection_success'] = 'Successfully connected to Cachenet API.';
$_LANG['cachenet']['admin']['connection_failed'] = 'Failed to connect to Cachenet API.';
$_LANG['cachenet']['admin']['purge_cache'] = 'Purge Cache';
$_LANG['cachenet']['admin']['force_ssl_renewal'] = 'Force SSL Renewal';
$_LANG['cachenet']['admin']['view_analytics'] = 'View Analytics';

?>