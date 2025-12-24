# Frontend Validation Guide: Peer Classification (US-N9)

This guide shows how to validate peer classification data in the frontend.

## Prerequisites

1. Backend API is running on `http://localhost:8000` (or configured `NEXT_PUBLIC_API_URL`)
2. Frontend is running on `http://localhost:3000` (or your dev server)
3. Peer classification data has been populated in the database

## Method 1: Browser DevTools - Network Tab

### Step 1: Open Browser DevTools
1. Open your browser (Chrome/Firefox/Edge)
2. Press `F12` or `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows)
3. Go to the **Network** tab

### Step 2: Navigate to Funds Page
1. Go to `http://localhost:3000/funds`
2. Wait for the page to load

### Step 3: Inspect API Response
1. In the Network tab, find the request to `/funds` (or `/api/funds`)
2. Click on the request
3. Go to the **Response** tab
4. Look for the JSON response

### Step 4: Verify peer_focus Field
Check that each fund object includes:
```json
{
  "fund_id": "K-INDIA-A(A)",
  "fund_name": "KASIKORN INDIA EQUITY FUND",
  "amc_name": "KASIKORN ASSET MANAGEMENT",
  "aimc_category": "India Equity",
  "aimc_category_source": "AIMC_CSV",
  "peer_focus": "India Equity",  // ← Should be present
  ...
}
```

**Expected:**
- ✅ `peer_focus` field exists in response
- ✅ `peer_focus` matches `aimc_category` (exact copy per US-N9)
- ✅ `aimc_category` is displayed correctly

## Method 2: Browser Console - Direct API Call

### Step 1: Open Browser Console
1. Open DevTools (`F12`)
2. Go to the **Console** tab

### Step 2: Test API Call
Paste this code in the console:

```javascript
// Test API endpoint
fetch('http://localhost:8000/funds?limit=5')
  .then(res => res.json())
  .then(data => {
    console.log('API Response:', data);
    console.log('Sample Fund:', data.items[0]);
    
    // Check peer_focus
    const sampleFund = data.items[0];
    console.log('peer_focus:', sampleFund.peer_focus);
    console.log('aimc_category:', sampleFund.aimc_category);
    console.log('Match:', sampleFund.peer_focus === sampleFund.aimc_category);
    
    // Count funds with peer_focus
    const withPeerFocus = data.items.filter(f => f.peer_focus).length;
    console.log(`Funds with peer_focus: ${withPeerFocus}/${data.items.length}`);
  })
  .catch(err => console.error('Error:', err));
```

**Expected Output:**
```
API Response: { items: [...], next_cursor: "...", ... }
Sample Fund: { fund_id: "...", peer_focus: "India Equity", ... }
peer_focus: "India Equity"
aimc_category: "India Equity"
Match: true
Funds with peer_focus: 5/5
```

## Method 3: Visual Inspection - Fund Cards

### Step 1: Navigate to Funds Page
1. Go to `http://localhost:3000/funds`
2. Wait for fund cards to load

### Step 2: Inspect Fund Cards
1. Look at the **"AIMC Type"** field in each fund card
2. Verify it displays the category correctly

**Expected Display:**
- Fund card shows: **"AIMC Type: India Equity"** (or similar)
- Category is displayed in green text (`.aimcType` class)
- If `aimc_category_source === 'SEC_API'`, shows `*` indicator

### Step 3: Inspect DOM Elements
1. Right-click on a fund card
2. Select **"Inspect"** or **"Inspect Element"**
3. Look for the AIMC Type element:

```html
<div class="detail">
  <span class="label">AIMC Type</span>
  <span class="value">
    <span class="aimcType">India Equity</span>
  </span>
</div>
```

## Method 4: React DevTools (Advanced)

### Step 1: Install React DevTools
1. Install [React Developer Tools](https://react.dev/learn/react-developer-tools) browser extension
2. Restart browser

### Step 2: Inspect Component Props
1. Open DevTools
2. Go to **Components** tab (React DevTools)
3. Select a `FundCard` component
4. Check the `fund` prop in the right panel

**Expected Props:**
```javascript
fund: {
  fund_id: "K-INDIA-A(A)",
  fund_name: "...",
  aimc_category: "India Equity",
  peer_focus: "India Equity",  // ← Should be present
  ...
}
```

## Method 5: TypeScript Type Checking

### Step 1: Check Type Definitions
Open `frontend/types/fund.ts` and verify:

```typescript
export interface FundSummary {
    fund_id: string;
    fund_name: string;
    amc_name: string;
    category: string | null;
    risk_level: string | null;
    aimc_category: string | null;  // ← Should exist
    aimc_category_source: string | null;  // ← Should exist
    peer_focus: string | null;  // ← Should exist (US-N9)
    ...
}
```

### Step 2: Run Type Check
```bash
cd frontend
npm run type-check  # or npx tsc --noEmit
```

**Expected:** No TypeScript errors related to `peer_focus`

## Method 6: Automated Test (Optional)

Create a test file to validate the API response:

```typescript
// frontend/__tests__/peer-classification.test.ts
import { fetchFunds } from '@/utils/api/funds';

describe('Peer Classification API', () => {
  it('should include peer_focus in fund response', async () => {
    const response = await fetchFunds(undefined, 10);
    
    expect(response.items.length).toBeGreaterThan(0);
    
    // Check that peer_focus exists
    response.items.forEach(fund => {
      if (fund.aimc_category) {
        // peer_focus should match aimc_category (exact copy)
        expect(fund.peer_focus).toBe(fund.aimc_category);
      }
    });
  });
});
```

## Common Issues & Solutions

### Issue 1: `peer_focus` is `undefined` in response
**Solution:**
- Check backend API is returning the field
- Verify database has peer classification data
- Run: `python -m scripts.reclassify_all_funds`

### Issue 2: `peer_focus` doesn't match `aimc_category`
**Solution:**
- This is expected per US-N9 (they should be the same)
- If different, check database: `SELECT peer_focus, aimc_category FROM fund WHERE peer_focus != aimc_category`

### Issue 3: Category not displaying in UI
**Solution:**
- Check browser console for errors
- Verify `formatCategoryLabel()` function is working
- Check CSS classes are applied correctly

### Issue 4: API returns 500 error
**Solution:**
- Check backend logs
- Verify database migration ran: `python -m app.services.ingestion.migrate_peer_classification_columns`
- Check database connection

## Quick Validation Checklist

- [ ] API response includes `peer_focus` field
- [ ] `peer_focus` matches `aimc_category` (exact copy)
- [ ] Fund cards display AIMC category correctly
- [ ] No console errors in browser
- [ ] TypeScript types are correct
- [ ] Category display works for funds with/without focus

## Sample Validation Script

Save this as `validate-frontend.html` and open in browser:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Peer Classification Validation</title>
</head>
<body>
    <h1>Peer Classification Validation</h1>
    <button onclick="testAPI()">Test API</button>
    <pre id="results"></pre>
    
    <script>
        async function testAPI() {
            const API_URL = 'http://localhost:8000';
            const results = document.getElementById('results');
            
            try {
                const response = await fetch(`${API_URL}/funds?limit=10`);
                const data = await response.json();
                
                const checks = {
                    totalFunds: data.items.length,
                    withPeerFocus: data.items.filter(f => f.peer_focus).length,
                    withAimcCategory: data.items.filter(f => f.aimc_category).length,
                    matching: data.items.filter(f => 
                        f.peer_focus && f.aimc_category && f.peer_focus === f.aimc_category
                    ).length,
                };
                
                results.textContent = JSON.stringify({
                    status: 'SUCCESS',
                    checks,
                    sampleFund: data.items[0],
                }, null, 2);
            } catch (error) {
                results.textContent = `ERROR: ${error.message}`;
            }
        }
    </script>
</body>
</html>
```

## Next Steps

After validation:
1. ✅ Verify peer_focus is in API response
2. ✅ Verify category displays correctly in FundCard
3. ✅ Test with different fund types (with/without AIMC category)
4. ✅ Test edge cases (null values, missing data)

