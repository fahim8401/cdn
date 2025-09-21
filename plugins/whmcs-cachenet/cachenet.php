<?php
/**
 * Cachenet CDN Plugin for WHMCS
 * 
 * @package     WHMCS
 * @copyright   2024 Cachenet
 * @license     MIT
 * @version     1.0.0
 * @author      Cachenet Team
 */

if (!defined("WHMCS")) {
    die("This file cannot be accessed directly");
}

/**
 * Define module related metadata
 */
function cachenet_MetaData()
{
    return array(
        'DisplayName' => 'Cachenet CDN',
        'APIVersion' => '1.1',
        'RequiresServer' => true,
    );
}

/**
 * Define product configuration options
 */
function cachenet_ConfigOptions()
{
    return array(
        'Cachenet API URL' => array(
            'Type' => 'text',
            'Size' => '50',
            'Default' => 'https://api.cachenet.example.com',
            'Description' => 'Cachenet API Base URL',
        ),
        'API Token' => array(
            'Type' => 'password',
            'Size' => '50',
            'Description' => 'Cachenet API Authentication Token',
        ),
        'Default Edge Regions' => array(
            'Type' => 'text',
            'Size' => '100',
            'Default' => 'us-east,us-west,eu-west,ap-southeast',
            'Description' => 'Comma-separated list of default edge regions',
        ),
        'Bandwidth Limit (GB)' => array(
            'Type' => 'text',
            'Size' => '10',
            'Default' => '100',
            'Description' => 'Monthly bandwidth limit in GB',
        ),
        'Auto-SSL' => array(
            'Type' => 'yesno',
            'Default' => 'yes',
            'Description' => 'Automatically issue SSL certificates',
        ),
    );
}

/**
 * Create account on service creation
 */
function cachenet_CreateAccount($vars)
{
    $apiUrl = $vars['configoption1'];
    $apiToken = $vars['configoption2'];
    $regions = $vars['configoption3'];
    $bandwidthLimit = $vars['configoption4'];
    $autoSSL = $vars['configoption5'];
    
    $domain = $vars['domain'];
    $clientEmail = $vars['clientsdetails']['email'];
    $clientName = $vars['clientsdetails']['firstname'] . ' ' . $vars['clientsdetails']['lastname'];
    
    // Create user account via API
    $userData = array(
        'email' => $clientEmail,
        'name' => $clientName,
        'password' => generateRandomPassword(),
        'role' => 'client',
        'bandwidth_limit' => $bandwidthLimit,
        'auto_ssl' => $autoSSL === 'on'
    );
    
    $userResponse = cachenet_apiCall($apiUrl, $apiToken, 'POST', '/auth/register', $userData);
    
    if (!$userResponse['success']) {
        return $userResponse['error'];
    }
    
    $userId = $userResponse['data']['user_id'];
    
    // Add domain to CDN
    $domainData = array(
        'domain' => $domain,
        'origin_ip' => '', // Will be configured by client
        'enabled' => false,
        'regions' => explode(',', $regions),
        'auto_ssl' => $autoSSL === 'on'
    );
    
    $domainResponse = cachenet_apiCall($apiUrl, $apiToken, 'POST', '/domains', $domainData);
    
    if (!$domainResponse['success']) {
        return $domainResponse['error'];
    }
    
    // Store account details
    $accountData = array(
        'user_id' => $userId,
        'domain_id' => $domainResponse['data']['domain_id'],
        'api_token' => $userResponse['data']['api_token']
    );
    
    return 'success';
}

/**
 * Suspend account
 */
function cachenet_SuspendAccount($vars)
{
    $apiUrl = $vars['configoption1'];
    $apiToken = $vars['configoption2'];
    $domain = $vars['domain'];
    
    // Disable CDN for domain
    $response = cachenet_apiCall($apiUrl, $apiToken, 'PUT', "/domains/{$domain}/disable", array());
    
    if (!$response['success']) {
        return $response['error'];
    }
    
    return 'success';
}

/**
 * Unsuspend account
 */
function cachenet_UnsuspendAccount($vars)
{
    $apiUrl = $vars['configoption1'];
    $apiToken = $vars['configoption2'];
    $domain = $vars['domain'];
    
    // Enable CDN for domain
    $response = cachenet_apiCall($apiUrl, $apiToken, 'PUT', "/domains/{$domain}/enable", array());
    
    if (!$response['success']) {
        return $response['error'];
    }
    
    return 'success';
}

/**
 * Terminate account
 */
function cachenet_TerminateAccount($vars)
{
    $apiUrl = $vars['configoption1'];
    $apiToken = $vars['configoption2'];
    $domain = $vars['domain'];
    
    // Remove domain from CDN
    $response = cachenet_apiCall($apiUrl, $apiToken, 'DELETE', "/domains/{$domain}", array());
    
    if (!$response['success']) {
        return $response['error'];
    }
    
    return 'success';
}

/**
 * Client area output
 */
function cachenet_ClientArea($vars)
{
    $apiUrl = $vars['configoption1'];
    $apiToken = $vars['configoption2'];
    $domain = $vars['domain'];
    
    // Get domain status and stats
    $response = cachenet_apiCall($apiUrl, $apiToken, 'GET', "/domains/{$domain}", array());
    
    if (!$response['success']) {
        return array('templatefile' => 'error', 'vars' => array('error' => $response['error']));
    }
    
    $domainData = $response['data'];
    
    // Get bandwidth usage
    $statsResponse = cachenet_apiCall($apiUrl, $apiToken, 'GET', "/cache/stats/{$domain}", array());
    $stats = $statsResponse['success'] ? $statsResponse['data'] : array();
    
    return array(
        'templatefile' => 'cachenet_clientarea',
        'vars' => array(
            'domain' => $domain,
            'cdn_enabled' => $domainData['enabled'],
            'ssl_enabled' => $domainData['ssl_enabled'],
            'origin_ip' => $domainData['origin_ip'],
            'cname_target' => $domainData['cname_target'],
            'bandwidth_used' => isset($stats['bandwidth_used']) ? $stats['bandwidth_used'] : 0,
            'bandwidth_limit' => $domainData['bandwidth_limit'],
            'cache_hit_ratio' => isset($stats['cache_hit_ratio']) ? $stats['cache_hit_ratio'] : 0,
            'regions' => $domainData['regions'],
            'api_url' => $apiUrl,
            'client_token' => $domainData['client_token']
        )
    );
}

/**
 * Admin area output
 */
function cachenet_AdminCustomButtonArray()
{
    return array(
        "Purge Cache" => "purgeCache",
        "Force SSL Renewal" => "renewSSL",
        "View Analytics" => "viewAnalytics",
    );
}

/**
 * Purge cache button
 */
function cachenet_purgeCache($vars)
{
    $apiUrl = $vars['configoption1'];
    $apiToken = $vars['configoption2'];
    $domain = $vars['domain'];
    
    $response = cachenet_apiCall($apiUrl, $apiToken, 'POST', "/cache/purge", array(
        'domain' => $domain,
        'purge_type' => 'all'
    ));
    
    if (!$response['success']) {
        return $response['error'];
    }
    
    return 'success';
}

/**
 * Renew SSL button
 */
function cachenet_renewSSL($vars)
{
    $apiUrl = $vars['configoption1'];
    $apiToken = $vars['configoption2'];
    $domain = $vars['domain'];
    
    $response = cachenet_apiCall($apiUrl, $apiToken, 'POST', "/ssl/renew", array(
        'domain' => $domain
    ));
    
    if (!$response['success']) {
        return $response['error'];
    }
    
    return 'success';
}

/**
 * View analytics button
 */
function cachenet_viewAnalytics($vars)
{
    $apiUrl = $vars['configoption1'];
    $domain = $vars['domain'];
    
    // Redirect to analytics dashboard
    header("Location: {$apiUrl}/analytics/{$domain}");
    exit;
}

/**
 * Make API call to Cachenet
 */
function cachenet_apiCall($apiUrl, $apiToken, $method, $endpoint, $data = array())
{
    $url = rtrim($apiUrl, '/') . $endpoint;
    
    $headers = array(
        'Authorization: Bearer ' . $apiToken,
        'Content-Type: application/json',
        'User-Agent: WHMCS-Cachenet/1.0'
    );
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    
    switch ($method) {
        case 'POST':
            curl_setopt($ch, CURLOPT_POST, true);
            if (!empty($data)) {
                curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
            }
            break;
        case 'PUT':
            curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'PUT');
            if (!empty($data)) {
                curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
            }
            break;
        case 'DELETE':
            curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'DELETE');
            break;
    }
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    
    if ($error) {
        return array('success' => false, 'error' => 'cURL Error: ' . $error);
    }
    
    $responseData = json_decode($response, true);
    
    if ($httpCode >= 200 && $httpCode < 300) {
        return array('success' => true, 'data' => $responseData);
    } else {
        $errorMessage = isset($responseData['error']) ? $responseData['error'] : 'HTTP Error: ' . $httpCode;
        return array('success' => false, 'error' => $errorMessage);
    }
}

/**
 * Generate random password
 */
function generateRandomPassword($length = 12)
{
    $characters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*';
    $password = '';
    for ($i = 0; $i < $length; $i++) {
        $password .= $characters[rand(0, strlen($characters) - 1)];
    }
    return $password;
}

/**
 * Test connection
 */
function cachenet_TestConnection($vars)
{
    $apiUrl = $vars['configoption1'];
    $apiToken = $vars['configoption2'];
    
    $response = cachenet_apiCall($apiUrl, $apiToken, 'GET', '/auth/me', array());
    
    if (!$response['success']) {
        return array('success' => false, 'error' => $response['error']);
    }
    
    return array('success' => true, 'error' => '');
}