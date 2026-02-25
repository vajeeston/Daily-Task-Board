# Daily Task Board — User Manual

<img src="app_icon.png" alt="Daily Task Board logo" width="72" style="border-radius:16px;">
<img src="app_icon.png" alt="Daily Task Board logo" style="display:block; width:100%; max-width:420px; height:auto; border-radius:16px; margin:0 auto;">

Daily Task Board helps you **plan**, **track**, and **finish** your daily work in one simple place.

This guide is written for everyday users (no technical knowledge needed).

---

## 1) Quick start (2 minutes)

1. Open the app.
2. In the **Calendar** (left), click a date (or press **Today**).
3. Click **Add Task**.
4. Fill in:
   - **Task** name
   - **Start** date/time
   - **Status**
   - Optional **Details** and **Attachments**
5. Click **Save**.

Good to know: the app also **auto-saves** your changes (so you don’t need a separate “Save file” step).

Tip: Double‑click a task (in the calendar list or the table) to edit quickly.

---

## 2) Screen layout

### Left side — Calendar panel
- **Calendar**: click a day to select it.
- **Today** button: jumps to today.
- **Add Task** button: creates a task for the selected day.
- **Tasks on selected date** list:
  - Shows tasks and notes for the selected date.
  - Colored by status (quick scan).
  - Double‑click an item to edit.

### Right side — Notice board
The notice board is organized into several tabs:

- **Dashboard**: a quick overview (today/week completions, streak, etc.)
- **Today**: today’s tasks + notes
- **Pending**: unfinished/working/postponed tasks (from any date)
- **Finished**: finished tasks (from any date)
- **Projects**: store small tool ideas/projects (links, code path, screenshots)

At the top you also see:
- **Status legend** (colors)
- **Quick Filter (Today)** to show only one status on the Today tab
- **Digital clock**

---

## 3) Understanding task statuses (and colors)

Each status has a consistent color across the app:

- **Unfinished** (light red): not started yet
- **Working** (light blue): currently in progress
- **Postponed** (light amber): delayed / rescheduled
- **Finished** (light green): completed

These colors appear in:
- The calendar highlights
- The “Tasks on selected date” list
- The tables in the notice board

---

## 4) Add a task (step‑by‑step)

1. Select a date in the **Calendar**.
2. Click **Add Task**.
3. Fill in:
   - **Task**: short, clear title (example: `Write report`)
   - **Start**: date and time you plan to begin
   - **Due (optional)**: a deadline (used for reminders if enabled)
   - **Status**: choose one (see section 3)
   - **Reminders (optional)**: at time / 10 minutes before / 1 hour before
4. Optional:
   - **Details**: add notes, checklists, links, or images
   - **Attachments**: add file paths you want to remember
5. Click **Save**.

---

## 5) Notes vs tasks

Sometimes you want a “sticky note” rather than a task.

In the task window:
- Enable **This is a note** to create a note.
- Notes appear in the **Today** tab and on the selected date list.
- Notes are displayed in a neutral style (not part of Pending/Finished tracking).

---

## 6) Edit or delete a task

### Edit
- In the table: select a row → click **Edit**
- Or double‑click a row
- Or double‑click an item in the calendar list

### Delete
- Select a task row → click **Delete**
- Confirm when asked

---

## 7) Quick Filter (Today tab)

At the top of the notice board you can set **Quick Filter (Today)**:

- **All (Today)**
- **Working only (Today)**
- **Unfinished only (Today)**
- **Postponed only (Today)**
- **Finished only (Today)**

This filter affects only the **Today** tab and is useful when you want to focus.

Notes still remain visible.

---

## 8) Notifications / reminders (Tasks + Projects)

If you set a **Start** time (or a **Due** time) you can enable reminders.

### How reminders work
- Reminders can be set to:
  - **At time**
  - **10 min before**
  - **1 hour before**
- The app checks reminders every **60 seconds**.
- Desktop notifications show:
  - **Title** (task/project title)
  - **First line of Details** (if you wrote any)

Tip: Notes do not send reminders.

### Projects reminders
Projects have an optional **Reminder time**. You can enable the same reminder options there.

---

## 9) Drag & drop scheduling

### Move a task to another day
1. In the **Calendar panel**, drag a task from **“Tasks on the selected date”**.
2. Drop it on the target day in the calendar.

The task keeps its time, but the **date changes**.

### Reorder tasks in Today
In the **Today** tab you can drag rows up/down to set a manual priority order.

---

## 10) Projects tab

Use **Projects** to store small tool ideas and ongoing work:
- Title + status
- Code folder/file path
- Links (one per line)
- Details (rich text)
- Screenshot thumbnails (attachments)

Projects can also have reminders.

---

## 11) Dashboard (light analytics)

The Dashboard gives quick signals without heavy charts:
- Tasks completed **today**
- Tasks completed **this week**
- Completion **streak** (consecutive days with at least one completion)
- Projects active **this month**
- Status distribution of tasks

---

## 12) Backup + restore

The app automatically keeps daily backups:
- Filename format: `daily_tasks_backup_YYYY-MM-DD.xlsx`
- Backups are stored in a `backups` folder next to your main XLSX file
- The app keeps the latest backups (default: 30 days)

### Restore from a backup
Menu: **File → Restore from backup…**

Choose a backup file and confirm. The current workbook will be replaced by the selected backup.

---

## 8) Details (text, checklists, images)

The **Details** field supports rich content:
- formatted text
- bullet lists
- checklists (simple manual style)
- images you insert

### Image preview (thumbnails)
When a task includes images, the “Details preview” panel shows them as **thumbnails** (smaller size) so the preview stays clean and readable.

---

## 9) Saving and opening your file

Your tasks are saved in an **Excel (.xlsx)** file.

### Save
- Click **Save** (toolbar or File → Save)

### Save As
- File → **Save As…**
- Choose a filename (example: `daily_tasks.xlsx`)

### Open
- Click **Open**
- Select your `.xlsx` file

Tip: The app usually remembers and reopens the **last file** you used.

### Excel colors (status + sheet tabs)
When you open your workbook in Excel, the app also adds **colors** for easier reading:
- Rows are tinted by status (Unfinished / Working / Postponed / Finished). Notes use a neutral gray tint.
- Sheet tabs are colored to match the sheet’s purpose (for example, Finished is green).

These colors are visual only — you can still sort/filter normally in Excel.

---

## 10) Printing and PDF export

You can print your tasks/projects or create a PDF.

### Print
1. Go to **File → Print…** (or press **Ctrl+P**).
2. Choose your printer and settings.
3. Click **Print**.

### Export all sheets to PDF
1. Go to **File → Export all sheets to PDF…**
2. In the options box, choose what to include:
   - ✅ **Include Details text** (prints the written details for each task/project)
   - ✅ **Include image thumbnails** (prints small thumbnails from Details, if any)
2. Choose a save location and filename.
3. Click **Save**.

**What is included in the PDF?**
- Tasks (All)
- Unfinished, Working, Postponed, Finished
- Notes
- Projects

Each section starts on a **new page**.

---

## 11) Settings — store your Excel file in OneDrive (optional)

By default, the app keeps its main workbook (`daily_tasks.xlsx`) in the **app folder**.

If you prefer to keep it in **OneDrive** (so it syncs automatically):

1. Open **Settings → Default file location…**
2. Choose **Use a custom folder (e.g., OneDrive)**
3. Click **Use OneDrive** (or **Browse…** to select a folder)
4. Click **OK**

After this, the app will use (and create if needed) the default workbook in that folder.

---

## 12) Appearance (Windows theme)

Daily Task Board uses the **Windows theme** for a familiar, native look and feel.
Status colors (Unfinished/Working/Postponed/Finished) are still shown throughout the app for quick scanning.

## 13) Toolbar & menus (what the buttons do)

### Toolbar
- **New**: start a new empty task file
- **Open**: open an existing `.xlsx`
- **Save**: save current file
- **Settings**: choose the default workbook location (app folder / OneDrive)
- **Help**: open the user manual
- **Close**: exit the app

### Menu bar
- **File**: New, Open, Save, Save As, Print, Export PDF, Exit
- **Settings**: Default file location…
- **Help**: User Manual (also opens with **F1**)

---

## 14) Tips for better productivity

- Use **Working** for tasks you are actively doing right now.
- Use **Postponed** instead of leaving old tasks unfinished.
- Use the **Quick Filter** when you want to focus on one status.
- Put meeting links, phone numbers, or key notes in **Details**.

---

## 15) Troubleshooting

**I can’t see status text clearly**
- Status colors are designed to stay readable.

**My image is too big**
- The preview shows thumbnails. Open the task to see full content.

**I can’t find my tasks**
- Check you opened the correct `.xlsx` file (File → Open).
- Check the date in the calendar.
- Check Pending/Finished tabs.

---

## Projects tab

The **Projects** tab is a place to track your small development projects (for example: Python tools, scripts, mini apps).  
It works like a “project dashboard” with a table + a Details preview.

### What you can store for each project

- **Project name**: the title shown in the Projects list
- **Status**:
  - **Unfinished** = planned / not started yet
  - **Working** = currently developing
  - **Postponed** = on hold / paused
  - **Finished** = completed
- **Code location**: the folder or main script path on your PC
- **Links**: one per line (GitHub, documentation, Trello, Notion, etc.)
- **Details**: rich notes + screenshots (images will show as thumbnails in the preview)
- **Attachments**: optional file paths to related PDFs/docs/data files

### Add a new project

1. Open the **Projects** tab.
2. Click **Add**.
3. Fill in:
   - Project name
   - Status
   - Code location (optional)
   - Links (optional)
   - Details (optional)
4. Click **Save**.

### Add screenshots (recommended)

- Use **Insert Image into Details** to add a screenshot.
- In the Projects list, when you select the project:
  - Text appears on the left
  - Screenshot thumbnails appear on the right

### Update project status quickly

In the Projects table, use the **Status dropdown** on each row to update progress instantly.

### Tips for good organization

- Keep a stable folder such as `Documents\My Tools\` to store project code so the path doesn’t change.
- Put important URLs (GitHub repo, docs, issues) into the **Links** field (one per line).
- Keep a short “how to run / what it does” note in **Details** so you can remember later.

---

© 2026 Daily Task Board. NV Soft, All rights reserved.

---
