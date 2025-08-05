# Document Generation Tools Guide

This guide explains how to use the new document generation tools in Bedrock Chat: PowerPoint Generator, Word Document Generator, and Excel Spreadsheet Generator.

## Overview

The document generation tools allow users to create professional documents directly through the chat interface using natural language prompts. The AI agent can automatically generate:

- **PowerPoint Presentations** (.pptx) - Multi-slide presentations with titles, content, and bullet points
- **Word Documents** (.docx) - Formatted documents with headings, paragraphs, and lists  
- **Excel Spreadsheets** (.xlsx) - Data tables with multiple sheets, headers, and formatting

## Setup and Configuration

### Backend Dependencies

The following Python packages are required and have been added to `pyproject.toml`:

```toml
python-pptx = "^1.0.2"    # PowerPoint generation
python-docx = "^1.1.2"    # Word document generation  
openpyxl = "^3.1.5"       # Excel spreadsheet generation
```

### Tool Registration

The tools are automatically registered as agent tools and available in the bot configuration interface:

- `generate_powerpoint` - PowerPoint Generator
- `generate_word_document` - Word Document Generator  
- `generate_excel_spreadsheet` - Excel Spreadsheet Generator

## How to Use

### 1. Enable Document Generation Tools

1. Go to **Bot Console** → **Create/Edit Bot**
2. Scroll to the **Agent** section
3. Enable the document generation tools you want to use:
   - ✅ PowerPoint Generator
   - ✅ Word Document Generator
   - ✅ Excel Spreadsheet Generator

### 2. Chat with Your Bot

Once enabled, you can request document generation through natural language:

#### PowerPoint Examples:
```
"Create a presentation about AI trends with 5 slides"
"Generate a PowerPoint for our quarterly review meeting"
"Make a presentation about our new product launch with bullet points"
```

#### Word Document Examples:
```
"Create a project report document with executive summary and findings"
"Generate a user manual for our software with step-by-step instructions"
"Write a meeting minutes document with action items"
```

#### Excel Spreadsheet Examples:
```
"Create a sales tracking spreadsheet with monthly data"
"Generate a budget analysis Excel file with multiple sheets"
"Make a project timeline spreadsheet with tasks and deadlines"
```

## Tool Capabilities

### PowerPoint Generator

**Features:**
- Multiple slide layouts (title slide, content slides)
- Customizable theme colors (blue, red, green, purple)
- Support for bullet points and paragraph content
- Professional formatting and styling
- Automatic title and subtitle generation

**Parameters:**
- `title`: Presentation title
- `slides`: Array of slide objects with title and content/bullet_points
- `theme_color`: Color theme (optional, default: blue)

**Example Structure:**
```json
{
  "title": "Quarterly Business Review",
  "slides": [
    {
      "title": "Executive Summary", 
      "content": "Overview of Q1 performance and key achievements"
    },
    {
      "title": "Key Metrics",
      "bullet_points": [
        "Revenue increased 15% YoY",
        "Customer satisfaction: 94%", 
        "New customers: 1,200"
      ]
    }
  ],
  "theme_color": "blue"
}
```

### Word Document Generator

**Features:**
- Multiple content types (headings, paragraphs, lists)
- Hierarchical heading levels (H1, H2, H3, etc.)
- Bullet and numbered lists
- Justified paragraph alignment
- Customizable font sizes
- Professional document formatting

**Parameters:**
- `title`: Document title
- `content`: Array of content sections with type and text/items
- `font_size`: Base font size (optional, default: 12)

**Content Types:**
- `heading`: Document headings with configurable levels
- `paragraph`: Regular text paragraphs
- `bullet_list`: Bulleted lists
- `numbered_list`: Numbered lists

**Example Structure:**
```json
{
  "title": "Project Documentation",
  "content": [
    {
      "type": "heading",
      "text": "Project Overview", 
      "level": 1
    },
    {
      "type": "paragraph",
      "text": "This project aims to improve customer experience..."
    },
    {
      "type": "bullet_list",
      "items": ["Requirement 1", "Requirement 2", "Requirement 3"]
    }
  ],
  "font_size": 12
}
```

### Excel Spreadsheet Generator

**Features:**
- Multiple worksheets/sheets
- Formatted headers with styling
- Auto-adjusted column widths
- Professional table formatting
- Support for various data types
- Header styling with colors and bold text

**Parameters:**
- `title`: Spreadsheet title/name
- `sheets`: Array of sheet objects with name, headers, and data
- `include_charts`: Whether to include charts (optional, default: false)

**Example Structure:**
```json
{
  "title": "Sales Analysis",
  "sheets": [
    {
      "name": "Q1 Data",
      "headers": ["Product", "Sales", "Revenue"],
      "data": [
        ["Product A", 100, 10000],
        ["Product B", 150, 15000]
      ]
    }
  ],
  "include_charts": false
}
```

## File Output

Generated documents are returned as base64-encoded files that can be:

- **Downloaded** directly from the chat interface
- **Viewed** inline (for supported formats)
- **Shared** via copy/paste functionality
- **Saved** to local storage

### File Formats:
- PowerPoint: `.pptx` format
- Word: `.docx` format  
- Excel: `.xlsx` format

## Advanced Usage Tips

### 1. Combining Tools
You can request multiple document types in a single conversation:
```
"Create a project proposal presentation, a detailed Word document with specifications, and an Excel budget spreadsheet"
```

### 2. Iterative Refinement
Ask for modifications to generated documents:
```
"Add two more slides to the presentation about market analysis"
"Include a conclusion section in the Word document"
"Add a summary sheet to the Excel file with totals"
```

### 3. Template-Based Generation
Provide specific templates or structures:
```
"Create a presentation using the standard company template with agenda, objectives, findings, and next steps"
```

## Troubleshooting

### Common Issues:

1. **Tool Not Available**: Ensure the document generation tools are enabled in your bot's agent configuration

2. **Generation Errors**: Check that your request includes sufficient detail for the AI to understand the desired document structure

3. **File Download Issues**: Ensure your browser allows downloads from the chat interface

4. **Large Documents**: Very large documents may take longer to generate - be patient during processing

### Error Messages:

- `"Error generating PowerPoint presentation"` - Check slide structure and content format
- `"Error generating Word document"` - Verify content array structure and types
- `"Error generating Excel spreadsheet"` - Check data format and sheet structure

## Examples and Use Cases

### Business Use Cases:
- **Quarterly Reports**: Generate comprehensive presentations with data visualizations
- **Project Documentation**: Create detailed Word documents with specifications
- **Budget Planning**: Build Excel spreadsheets with financial projections
- **Meeting Materials**: Produce presentation slides and supporting documents
- **Training Materials**: Create educational content with multiple document types

### Educational Use Cases:
- **Research Papers**: Generate structured Word documents with citations
- **Data Analysis**: Create Excel spreadsheets with statistical data
- **Presentations**: Build educational slide decks for lectures
- **Lab Reports**: Produce formatted scientific documents

### Personal Use Cases:
- **Event Planning**: Create presentation materials and planning spreadsheets
- **Home Budgeting**: Generate personal finance tracking spreadsheets
- **Travel Planning**: Build itinerary documents and budget trackers

## API Integration

For developers integrating with the document generation tools programmatically, the tools are available through the standard agent tool API endpoints with the following tool names:

- `generate_powerpoint`
- `generate_word_document` 
- `generate_excel_spreadsheet`

Each tool accepts JSON parameters as defined in their respective schemas and returns base64-encoded document data.

## Future Enhancements

Planned improvements include:
- Chart and graph generation in Excel
- Custom PowerPoint templates
- Advanced Word document formatting
- PDF export capabilities
- Collaborative editing features
- Integration with cloud storage services

---

**Need Help?** 
If you encounter issues or have questions about the document generation tools, please refer to the main Bedrock Chat documentation or contact support.