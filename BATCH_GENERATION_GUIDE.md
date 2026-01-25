# Batch Post Generation & Post Templates - User Guide

## Overview
Two powerful new features have been added to help you maintain consistent LinkedIn posting:

1. **Post Templates/Variety** - Generate different types of posts to keep your content diverse
2. **Batch Post Generation** - Create a week's worth of posts in one sitting

These features work together to help you:
- Save time by generating multiple posts at once
- Keep your content fresh with various post formats
- Plan your posting schedule in advance
- Maintain consistency without daily effort

---

## Feature 1: Post Templates

### What Are Post Templates?

Post templates are different writing styles and formats for your LinkedIn posts. Instead of every post sounding the same, you can choose from 7 different formats:

### Available Formats

1. **📝 Standard Post**
   - Traditional informative post
   - Balanced and professional
   - Good for general topics
   - Example: "Just came across this interesting development in AI..."

2. **💡 Insight & Analysis**
   - Deep dive with unique perspective
   - Positions you as a thought leader
   - Shows expertise and analysis
   - Example: "Here's what this trend means for the future of tech..."

3. **📖 Personal Story**
   - Shares relevant personal experience
   - Makes content relatable and human
   - Builds authentic connection
   - Example: "This reminds me of when we first encountered..."

4. **❓ Thought-Provoking Question**
   - Asks your network for opinions
   - Encourages engagement and discussion
   - Great for starting conversations
   - Example: "What's your take on this development?"

5. **🔥 Hot Take**
   - Bold or contrarian opinion
   - Shows conviction and personality
   - Gets attention and engagement
   - Example: "Unpopular opinion: This trend is overrated..."

6. **🎓 Educational/Tutorial**
   - Teaches something valuable
   - Breaks down complex concepts
   - Provides clear value
   - Example: "Here's what you need to know about..."

7. **📋 Listicle**
   - 3-5 key points in numbered format
   - Scannable and punchy
   - Easy to digest
   - Example: "5 reasons why this matters for developers:"

### How to Use Post Templates

#### Method 1: When Creating Individual Posts
1. Go to the post generation page
2. Select a trend
3. Choose a post format from the dropdown
4. Click "Generate Post"

#### Method 2: In Batch Generation (Recommended)
See the Batch Generation section below.

---

## Feature 2: Batch Post Generation

### What Is Batch Generation?

Batch generation allows you to create multiple posts at once from your top trends. This is perfect for:
- Planning a week of content in one session
- Ensuring you never run out of posts
- Maintaining consistent posting when busy
- Reviewing and scheduling multiple posts together

### How to Use Batch Generation

#### Step 1: Access Batch Generation
- Click "Batch Generate" in the main navigation
- Or visit: http://localhost:4321/batch-generate

#### Step 2: Select Number of Posts
1. Choose how many posts you want to generate:
   - 3 posts (light week)
   - 5 posts (recommended)
   - 7 posts (full week, one per day)
   - 10 posts (two weeks)

2. Click "Load Top Trends"

3. The system will load the highest-scoring trends from your latest search

#### Step 3: Review Selected Trends
- Review the trends that were selected
- Each trend shows:
  - Title and description
  - Relevance score
  - Category
  - Numbered order (1, 2, 3, etc.)

#### Step 4: Assign Post Formats
1. Click "Next: Choose Formats"

2. For each trend, select a post format from the dropdown

3. **Pro Tip**: Click "Auto-Distribute Formats" to automatically assign different formats to each post for maximum variety

4. The formats will cycle through:
   - Post 1: Standard
   - Post 2: Insight
   - Post 3: Story
   - Post 4: Question
   - Post 5: Educational
   - Post 6: List
   - Post 7: Hot Take

#### Step 5: Generate Posts
1. Click "Generate Posts"

2. Wait while the LLM generates all posts (this may take 1-2 minutes)

3. You'll see a progress indicator

#### Step 6: Review Generated Posts
- See summary of successful and failed posts
- Each generated post shows:
  - Title of the trend
  - Post format used
  - Quick links to edit or approve

#### Step 7: Approve & Schedule

**Option A: Manual Review**
1. Click "Edit" on each post to review and refine
2. Manually approve each post
3. Schedule individually

**Option B: Bulk Actions (Recommended)**
1. Click "Approve All" to approve all generated posts at once
2. Click "Schedule All" to automatically schedule posts over the next week

**Automatic Scheduling** spreads posts evenly:
- For 5 posts: One every ~1.4 days
- For 7 posts: One per day
- Posts scheduled at different times (9am, 12pm, 3pm rotation)

---

## Best Practices

### For Content Variety
1. **Use different formats** - Don't use the same format twice in a row
2. **Match format to topic** - Use educational for tutorials, story for experiences, hot take for controversial topics
3. **Balance styles** - Mix analytical (insight) with personal (story) with engaging (question)

### For Batch Generation
1. **Weekly batch sessions** - Set aside 30 minutes once a week
2. **Generate 5-7 posts** - One week of content
3. **Auto-distribute formats** - Let the system vary the styles
4. **Review before scheduling** - Quickly scan each post
5. **Schedule evenly** - Spread posts throughout the week

### For Consistency
1. **Monday morning routine** - Generate posts for the week ahead
2. **Use the scheduler** - Don't rely on manual posting
3. **Keep posts in pipeline** - Always have 3-5 posts ready
4. **Track what works** - Note which formats get more engagement

---

## Example Workflow

**Goal**: Post to LinkedIn 5x per week without daily effort

**Monday Morning (30 minutes)**:
1. Open Batch Generate page
2. Select "7 posts"
3. Load top trends
4. Click "Auto-Distribute Formats"
5. Generate posts
6. Quick review (2-3 minutes per post)
7. Minor edits if needed
8. Click "Schedule All"

**Result**: Full week of LinkedIn posts scheduled automatically!

**Rest of Week**:
- Posts publish automatically at scheduled times
- You can check engagement and respond to comments
- No daily content creation needed

---

## API Endpoints (For Advanced Users)

### Post Formats
- `GET /api/post-formats` - List all available formats

### Batch Generation
- `POST /api/posts/batch` - Generate multiple posts
  ```json
  {
    "trend_ids": [1, 2, 3, 4, 5],
    "post_formats": ["standard", "insight", "story", "question", "educational"],
    "default_format": "standard"
  }
  ```

### Bulk Operations
- `POST /api/posts/bulk-approve` - Approve multiple posts
  ```json
  {
    "post_ids": [10, 11, 12, 13, 14]
  }
  ```

- `POST /api/posts/bulk-schedule` - Schedule multiple posts
  ```json
  {
    "post_ids": [10, 11, 12],
    "scheduled_times": ["2026-01-26T09:00:00", "2026-01-27T12:00:00", "2026-01-28T15:00:00"]
  }
  ```

---

## Troubleshooting

### "No trends found"
- Run a search query first on the Research page
- Make sure you have keywords/phrases configured

### Posts not generating
- Check that Ollama is running
- Verify LLM model is available
- Check API logs for errors

### Bulk schedule not working
- Make sure all posts are approved first
- Posts must be in "approved" status to schedule
- Check that scheduled times are in the future

### Format not showing on posts
- Format is saved in database but may show as "standard" for old posts
- Only new posts will show custom formats
- Restart API if format not appearing

---

## Tips for Maximum Engagement

### Format Selection by Goal

**To educate your network**: Use Educational format
**To spark discussion**: Use Question format
**To share experience**: Use Story format
**To show expertise**: Use Insight format
**To stand out**: Use Hot Take format
**To provide value quickly**: Use List format
**For general topics**: Use Standard format

### Mixing Formats in a Week

**Monday**: Insight (start week strong with analysis)
**Tuesday**: Educational (provide value)
**Wednesday**: Story (mid-week relatability)
**Thursday**: Question (boost engagement)
**Friday**: List (easy Friday reading)
**Saturday**: Hot Take (weekend controversial opinion)
**Sunday**: Standard (general topic for slow day)

---

## Success Metrics

After using these features, you should see:
- ✅ More consistent posting (5-7x per week)
- ✅ Higher engagement variety (different posts perform differently)
- ✅ Less time spent on content creation (30 min/week vs 2+ hours)
- ✅ No missed posting days
- ✅ More diverse content that appeals to different audience segments

---

## Quick Start Checklist

- [ ] Run a trend search to populate trends
- [ ] Navigate to "Batch Generate"
- [ ] Select "5 posts" and load trends
- [ ] Click "Auto-Distribute Formats"
- [ ] Generate posts
- [ ] Quick review (5-10 minutes total)
- [ ] Click "Schedule All"
- [ ] Check schedule page to confirm
- [ ] Repeat next Monday!

**Result**: Consistent LinkedIn presence with minimal daily effort!
