// --- Configuration ---
const SPREADSHEET_ID = '1hm65OkFaG4J_CDJ8youSt3hYItof2n18ENnhm-hTESk';
const SHEET_USERS = 'UserEntries';
const SHEET_GROUPS = 'Groups';

// --- Main Webhook Entry Point ---
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const intent = data.queryResult.intent.displayName;
    const params = data.queryResult.parameters;
    const session = data.session;

    const contextParams = getContextParams(
      data.queryResult.outputContexts,
      "awaiting_confirmation"
    );

    let response = {};

    if (intent === 'Find Ride') {
      response = handleFindRide(params, session);
    } 
    else if (intent === 'Check Status') {
      response = handleCheckStatus(params);
    } 
    else if (intent === 'Confirm Group') {
      response = handleConfirmation(true, contextParams);
    } 
    else if (intent === 'Reject Group') {
      response = handleConfirmation(false, contextParams);
    } 
    else if (intent === 'Check Available Rides') {
      response = handleCheckAvailableRides(params);
    } 
    else {
      response = { fulfillmentText: "I'm not sure how to help with that." };
    }

    return ContentService.createTextOutput(JSON.stringify(response))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      fulfillmentText: "Backend error: " + error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// --- Helpers ---

function getContextParams(contexts, suffix) {
  if (!contexts) return null;
  for (const ctx of contexts) {
    if (ctx.name.endsWith(suffix)) return ctx.parameters;
  }
  return null;
}

function getString(param) {
  if (!param) return "";
  if (typeof param === 'string') return param;
  if (Array.isArray(param)) return param.length ? getString(param[0]) : "";
  if (typeof param === 'object') return param.name || param.value || "";
  return String(param);
}

function normalizeDate(dateStr) {
  if (!dateStr) return "";
  if (dateStr.includes('T')) return dateStr.split('T')[0];
  return dateStr;
}

// --- NEW FEATURE HANDLER ---

function handleCheckAvailableRides(params) {
  let dateStr = getString(params['date']);
  if (!dateStr) {
    dateStr = new Date().toISOString();
  }

  const targetDate = normalizeDate(dateStr);
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_GROUPS);
  const data = sheet.getDataRange().getValues();

  let results = [];

  for (let i = 1; i < data.length; i++) {
    const groupId = data[i][0];
    const loc = data[i][1];
    const date = normalizeDate(String(data[i][2]));
    const time = data[i][3];

    if (date === targetDate) {
      results.push(`• Group ${groupId} at ${time} (${loc})`);
    }
  }

  if (results.length === 0) {
    return {
      fulfillmentText: `There are no rides available for ${targetDate}.`
    };
  }

  return {
    fulfillmentText:
      `Here are the available rides for ${targetDate}:\n` +
      results.join("\n")
  };
}

// --- EXISTING LOGIC (UNCHANGED) ---

function handleFindRide(params, session) {
  const name = getString(params['given-name']) || "Unknown";
  const phone = getString(params['phone-number']) || "0000";
  const location = getString(params['location']) || "Campus";
  const dateStr = getString(params['date']) || new Date().toISOString();
  const timeStr = getString(params['time']) || "12:00";

  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_USERS);
  sheet.appendRow([new Date(), phone, name, location, dateStr, timeStr, "", "Pending"]);

  const matches = findMatches(location, dateStr, timeStr, phone);
  let responseText = "";
  let outputContexts = [];

  if (matches.length > 0) {
    responseText = `Success, ${name}. I found ${matches.length} other(s) for ${location}. Reply 'Yes' to confirm group.`;
    outputContexts = [{
      name: session + "/contexts/awaiting_confirmation",
      lifespanCount: 2,
      parameters: { phone, name }
    }];
  } else {
    responseText = `Registered for ${location}. No matches yet.`;
  }

  return { fulfillmentText: responseText, outputContexts };
}

function handleCheckStatus(params) {
  const phone = getString(params['phone-number']);
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_USERS);
  const data = sheet.getDataRange().getValues();

  for (let i = 1; i < data.length; i++) {
    if (String(data[i][1]) === String(phone)) {
      return {
        fulfillmentText: `Status: ${data[i][7]}, Group: ${data[i][6] || "None"}`
      };
    }
  }
  return { fulfillmentText: "No record found." };
}

function handleConfirmation(isConfirmed, contextParams) {
  if (!contextParams || !contextParams.phone) {
    return { fulfillmentText: "Session expired. Please try again." };
  }

  const phone = contextParams.phone;
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_USERS);
  const data = sheet.getDataRange().getValues();

  for (let i = 1; i < data.length; i++) {
    if (String(data[i][1]) === String(phone)) {
      if (isConfirmed) {
        sheet.getRange(i + 1, 8).setValue("Confirmed");
        return { fulfillmentText: "✅ Group confirmed successfully!" };
      } else {
        return { fulfillmentText: "No problem, keeping your request pending." };
      }
    }
  }
  return { fulfillmentText: "User not found." };
}

function findMatches(location, dateStr, timeStr, phone) {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_USERS);
  const data = sheet.getDataRange().getValues();
  const targetDate = normalizeDate(dateStr);

  return data.filter((r, i) =>
    i > 0 &&
    r[1] !== phone &&
    String(r[3]).toLowerCase() === String(location).toLowerCase() &&
    normalizeDate(String(r[4])) === targetDate
  );
}
