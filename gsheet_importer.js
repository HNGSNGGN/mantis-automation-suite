function updateMantisFromAttachment() {
  const spreadsheetId = 'YOUR_SPREADSHEET_ID_HERE';
  const sheetName = 'MANTIS';
  const ss = SpreadsheetApp.openById(spreadsheetId);
  const sheet = ss.getSheetByName(sheetName);

  // 「MANTIS」という件名の直近のメールスレッドを検索
  const threads = GmailApp.search('subject:(MANTIS CSV) has:attachment', 0, 10);
  if (threads.length === 0) {
    sheet.getRange('A1').setValue('❌ 添付ファイル付きの「MANTIS CSV」メールが見つかりません。');
    return;
  }

  const messages = threads[0].getMessages();
  const latestMessage = messages[messages.length - 1];
  const attachments = latestMessage.getAttachments();

  // CSV添付ファイルを探す
  const csvAttachment = attachments.find(att => att.getContentType() === 'text/csv' || att.getName().endsWith('.csv'));
  if (!csvAttachment) {
    sheet.getRange('A1').setValue('❌ CSV添付ファイルが見つかりません。');
    return;
  }

  const csvContent = csvAttachment.getDataAsString("utf-8");

  // CSVをパース
  const rows = Utilities.parseCsv(csvContent);

  // シートを初期化し、データを記録
  sheet.clearContents();
  sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
