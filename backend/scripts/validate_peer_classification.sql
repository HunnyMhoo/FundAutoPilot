-- Validation queries for peer classification data
-- Run these queries to validate peer classification results

-- 1. Sample funds with peer classification (first 20)
SELECT 
    proj_id,
    class_abbr_name,
    fund_abbr,
    fund_name_en,
    aimc_category,
    peer_focus,
    peer_currency,
    peer_fx_hedged_flag,
    peer_distribution_policy,
    peer_key,
    peer_key_fallback_level
FROM fund 
WHERE fund_status = 'RG' 
    AND peer_key IS NOT NULL
ORDER BY peer_key, proj_id
LIMIT 20;

-- 2. Coverage statistics
SELECT 
    COUNT(*) as total_funds,
    COUNT(peer_key) as funds_with_peer_key,
    ROUND(COUNT(peer_key)::numeric / COUNT(*) * 100, 2) as coverage_pct,
    COUNT(DISTINCT peer_key) as unique_peer_groups,
    COUNT(DISTINCT aimc_category) as unique_aimc_categories
FROM fund 
WHERE fund_status = 'RG';

-- 3. Fallback level distribution
SELECT 
    peer_key_fallback_level,
    COUNT(*) as fund_count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM fund WHERE fund_status = 'RG' AND peer_key IS NOT NULL) * 100, 2) as percentage
FROM fund 
WHERE fund_status = 'RG' 
    AND peer_key IS NOT NULL
GROUP BY peer_key_fallback_level
ORDER BY peer_key_fallback_level;

-- 4. Peer focus distribution (top 20)
SELECT 
    peer_focus,
    COUNT(*) as fund_count
FROM fund 
WHERE fund_status = 'RG' 
    AND peer_focus IS NOT NULL
GROUP BY peer_focus
ORDER BY fund_count DESC
LIMIT 20;

-- 5. Currency distribution
SELECT 
    peer_currency,
    COUNT(*) as fund_count
FROM fund 
WHERE fund_status = 'RG' 
    AND peer_currency IS NOT NULL
GROUP BY peer_currency
ORDER BY fund_count DESC;

-- 6. FX hedge flag distribution
SELECT 
    peer_fx_hedged_flag,
    COUNT(*) as fund_count
FROM fund 
WHERE fund_status = 'RG' 
    AND peer_fx_hedged_flag IS NOT NULL
GROUP BY peer_fx_hedged_flag
ORDER BY fund_count DESC;

-- 7. Distribution policy distribution
SELECT 
    peer_distribution_policy,
    COUNT(*) as fund_count
FROM fund 
WHERE fund_status = 'RG' 
    AND peer_distribution_policy IS NOT NULL
GROUP BY peer_distribution_policy
ORDER BY fund_count DESC;

-- 8. Sample peer keys (showing different patterns)
SELECT DISTINCT
    peer_key,
    COUNT(*) as fund_count,
    peer_key_fallback_level
FROM fund 
WHERE fund_status = 'RG' 
    AND peer_key IS NOT NULL
GROUP BY peer_key, peer_key_fallback_level
ORDER BY fund_count DESC
LIMIT 20;

-- 9. Funds with missing peer_key (to investigate)
SELECT 
    proj_id,
    class_abbr_name,
    fund_abbr,
    aimc_category,
    peer_focus,
    peer_currency,
    peer_fx_hedged_flag,
    peer_distribution_policy
FROM fund 
WHERE fund_status = 'RG' 
    AND peer_key IS NULL
LIMIT 20;

-- 10. Verify peer_focus matches aimc_category (should be same)
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN peer_focus = aimc_category THEN 1 END) as matching,
    COUNT(CASE WHEN peer_focus != aimc_category THEN 1 END) as different,
    COUNT(CASE WHEN peer_focus IS NULL AND aimc_category IS NOT NULL THEN 1 END) as missing_focus,
    COUNT(CASE WHEN peer_focus IS NOT NULL AND aimc_category IS NULL THEN 1 END) as missing_category
FROM fund 
WHERE fund_status = 'RG';

-- 11. Funds with share classes (verify each class gets its own peer_key)
SELECT 
    proj_id,
    COUNT(DISTINCT class_abbr_name) as class_count,
    COUNT(DISTINCT peer_key) as distinct_peer_keys,
    STRING_AGG(DISTINCT peer_key, ', ') as peer_keys
FROM fund 
WHERE fund_status = 'RG' 
    AND peer_key IS NOT NULL
GROUP BY proj_id
HAVING COUNT(DISTINCT class_abbr_name) > 1
LIMIT 10;

