// --- Configuration ---
const SPREADSHEET_ID = '1hm65OkFaG4J_CDJ8youSt3hYItof2n18ENnhm-hTESk'; // Replace with actual ID
const SHEET_USERS = 'UserEntries';
const SHEET_GROUPS = 'Groups';

// --- Main Webhook Entry Point ---
function doPost(e) {
    try {
        const data = JSON.parse(e.postData.contents);
        const intent = data.queryResult.intent.displayName;
        const params = data.queryResult.parameters;
        const session = data.session;

        // Extract outputContexts from request if they exist (for Confirm Group)
        const contextParams = getContextParams(data.queryResult.outputContexts, "awaiting_confirmation");

        let response = {};

        if (intent === 'Find Ride') {
            response = handleFindRide(params, session);
        } else if (intent === 'Check Status') {
            response = handleCheckStatus(params);
        } else if (intent === 'Confirm Group') {
            response = handleConfirmation(params, true, contextParams);
        } else if (intent === 'Reject Group') {
            response = handleConfirmation(params, false, contextParams);
        } else {
            response = { fulfillmentText: "I'm not sure how to help with that." };
        }

        return ContentService.createTextOutput(JSON.stringify(response))
            .setMimeType(ContentService.MimeType.JSON);

    } catch (error) {
        return ContentService.createTextOutput(JSON.stringify({
            "fulfillmentText": "Error in backend logic: " + error.toString()
        })).setMimeType(ContentService.MimeType.JSON);
    }
}

// Helper to find specific context parameters
function getContextParams(contexts, contextNameSuffix) {
    if (!contexts) return null;
    for (const ctx of contexts) {
        if (ctx.name.endsWith(contextNameSuffix)) {
            return ctx.parameters;
        }
    }
    return null;
}

// --- Logic Handlers ---

function getString(param) {
    if (!param) return "";
    if (typeof param === 'string') return param;

    if (Array.isArray(param)) {
        if (param.length > 0) return getString(param[0]);
        return "";
    }

    if (typeof param === 'object') {
        if (param['business-name']) return param['business-name'];
        if (param['city']) return param['city'];
        if (param['admin-area']) return param['admin-area'];

        return param.name || param.value || JSON.stringify(param);
    }
    return String(param);
}

function handleFindRide(params, session) {
    const name = getString(params['given-name']) || getString(params['name']) || "Unknown";
    const phone = getString(params['phone-number']) || "0000";
    const location = getString(params['location']) || "Campus";
    const dateStr = getString(params['date']) || new Date().toISOString();
    let timeStr = getString(params['time']) || "12:00";

    const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_USERS);

    // 1. Save Entry
    const userId = phone;
    sheet.appendRow([new Date(), userId, name, location, dateStr, timeStr, "", "Pending"]);

    // 2. Grouping Check
    const matches = findMatches(location, dateStr, timeStr, userId);

    let responseText = "";
    let outputContexts = [];

    if (matches.length > 0) {
        responseText = `Success, ${name}. I found ${matches.length} other(s) for ${location}. Reply 'Yes' to confirm group.`;
        // Store context for next turn
        outputContexts = [{
            name: session + "/contexts/awaiting_confirmation",
            lifespanCount: 2,
            parameters: {
                "phone": userId,
                "name": name
            }
        }];
    } else {
        let displayTime = timeStr.includes('T') ? timeStr.split('T')[1].substring(0, 5) : timeStr;
        responseText = `Got it, ${name}. Registered for ${location} at approx ${displayTime}. No matches yet.`;
    }

    return {
        fulfillmentText: responseText,
        outputContexts: outputContexts
    };
}

function findMatches(location, dateStr, timeStr, currentUserId) {
    const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_USERS);
    const data = sheet.getDataRange().getValues();
    const matches = [];

    function getHour(tStr) {
        if (!tStr) return 0;
        if (typeof tStr !== 'string') return 0;
        if (tStr.includes('T')) {
            const part = tStr.split('T')[1];
            return parseInt(part.split(':')[0]);
        }
        if (tStr.includes(':')) {
            return parseInt(tStr.split(':')[0]);
        }
        return 0;
    }

    const targetHour = getHour(timeStr);
    const targetDateOnly = dateStr.includes('T') ? dateStr.split('T')[0] : dateStr;

    for (let i = 1; i < data.length; i++) {
        const row = data[i];
        const uId = row[1];
        const uLoc = row[3];
        const uDate = row[4];
        const uTime = row[5];
        const uStatus = row[7];

        let uDateStr = uDate;
        if (typeof uDate === 'object') {
            try { uDateStr = uDate.toISOString(); } catch (e) { uDateStr = String(uDate); }
        }
        const uDateOnly = uDateStr.includes('T') ? uDateStr.split('T')[0] : uDateStr;

        // FIXED: Case-Insensitive Location Match AND Allow Confirmed users
        const uLocStr = String(uLoc).toLowerCase();
        const locStr = String(location).toLowerCase();
        const isStatusMatch = (uStatus === 'Pending' || uStatus === 'Confirmed');

        if (uId !== currentUserId && uLocStr === locStr && isStatusMatch) {
            if (uDateOnly === targetDateOnly) {
                const uHour = getHour(uTime);
                if (Math.abs(uHour - targetHour) <= 2) {
                    matches.push(row);
                }
            }
        }
    }
    return matches;
}

function handleCheckStatus(params) {
    const phone = getString(params['phone-number']);
    if (!phone) return { fulfillmentText: "I need your phone number to check." };

    const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_USERS);
    const data = sheet.getDataRange().getValues();

    for (let i = 1; i < data.length; i++) {
        if (String(data[i][1]) === String(phone)) {
            const status = data[i][7];
            const grp = data[i][6];
            return { fulfillmentText: `Found you. Location: ${data[i][3]}. Status: ${status}. GroupID: ${grp || "None"}` };
        }
    }
    return { fulfillmentText: "I couldn't find a pending request for that number." };
}

function handleConfirmation(params, isConfirmed, contextParams) {
    const phone = contextParams ? contextParams.phone : null;

    if (!phone) {
        return { fulfillmentText: "Session expired. I don't know who is confirming. Please Find a Ride again." };
    }

    if (isConfirmed) {
        const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_USERS);
        const data = sheet.getDataRange().getValues();

        let userRowIndex = -1;
        let userDetails = null;

        for (let i = 1; i < data.length; i++) {
            if (String(data[i][1]) === String(phone)) {
                userRowIndex = i;
                userDetails = data[i];
                break;
            }
        }

        if (userRowIndex === -1) {
            return { fulfillmentText: "Error: Could not find your record to confirm." };
        }

        const loc = userDetails[3];
        const date = userDetails[4];
        const time = userDetails[5];

        let dateStr = date;
        if (typeof date === 'object') { try { dateStr = date.toISOString(); } catch (e) { dateStr = String(date); } }
        let timeStr = time;
        if (typeof time === 'object') { try { timeStr = time.toISOString(); } catch (e) { timeStr = String(time); } }

        const matches = findMatches(loc, dateStr, timeStr, phone);

        let finalGroupId = "";

        for (const m of matches) {
            const mGroupId = m[6];
            if (mGroupId) {
                finalGroupId = mGroupId;
                break;
            }
        }

        if (!finalGroupId) {
            finalGroupId = "GRP-" + Math.floor(Math.random() * 10000);
            const groupSheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_GROUPS);
            groupSheet.appendRow([finalGroupId, loc, dateStr, timeStr, phone, "Forming"]);
        }

        sheet.getRange(userRowIndex + 1, 7).setValue(finalGroupId);
        sheet.getRange(userRowIndex + 1, 8).setValue("Confirmed");

        return { fulfillmentText: `Great! You are confirmed in group ${finalGroupId}.` };
    } else {
        return { fulfillmentText: "Understood. Maintaining status as Pending." };
    }
}
