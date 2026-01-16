# Report Templates User Guide

## Overview

The Report Templates system allows you to create custom report templates and generate reports on-demand with your preferred sections and format.

## Features

- **Custom Templates**: Create templates with configurable sections
- **Multiple Formats**: PDF, Excel, CSV, JSON, HTML
- **Section Selection**: Choose which analysis sections to include
- **Template Management**: Create, update, delete templates
- **Report History**: Track all generated reports
- **On-Demand Generation**: Generate reports anytime from the dashboard

## Accessing Report Templates

1. Launch the dashboard: `streamlit run src/app/dashboard/app.py`
2. Navigate to **Utilities** section in the sidebar
3. Click **📄 Report Templates**

## Creating a Template

### Step 1: Navigate to Create Template Tab

1. Go to **📄 Report Templates** page
2. Click the **➕ Create Template** tab

### Step 2: Configure Template

1. **Template Name**: Enter a descriptive name (e.g., "Monthly Portfolio Report")

2. **Description**: Optional description of the template's purpose

3. **Output Format**: Choose from:
   - **PDF**: Professional PDF report (recommended for sharing)
   - **Excel**: Spreadsheet format with multiple sheets
   - **CSV**: Simple CSV format
   - **JSON**: Machine-readable JSON format
   - **HTML**: Web-friendly HTML format

4. **Sections**: Select which sections to include:
   - ✅ **Executive Summary**: High-level overview
   - ✅ **Performance Metrics**: Key performance indicators
   - ✅ **Portfolio Composition**: Holdings and weights
   - ✅ **Risk Analysis**: Risk metrics and warnings
   - ✅ **Recommendations**: AI-generated recommendations
   - ✅ **Attribution**: Performance attribution analysis
   - ✅ **Benchmark Comparison**: Comparison vs benchmarks
   - ✅ **Factor Exposure**: Factor exposure analysis

5. Click **Create Template**

## Generating Reports

### Step 1: Navigate to Generate Report Tab

1. Go to **📄 Report Templates** page
2. Click the **📊 Generate Report** tab

### Step 2: Select Template and Run

1. **Select Template**: Choose from your enabled templates
2. **Select Run**: Choose the analysis run to generate report for
3. Click **📊 Generate Report**

### Step 3: Download Report

1. Wait for generation to complete
2. Report details will be shown:
   - File path
   - File size
3. Click **📥 Download Report** to download

## Managing Templates

### Viewing Templates

1. Go to **📋 Templates** tab
2. View all templates with:
   - Name and format
   - Description
   - Status (enabled/disabled)
   - Created date
   - Last generated date
   - Included sections

### Editing Templates

Currently, editing is done by deleting and recreating templates. Full edit functionality coming soon.

### Deleting Templates

1. Find the template
2. Click **🗑️ Delete** button
3. Confirm deletion

**Note**: Deleting a template does not delete generated reports.

## Viewing Report History

1. Go to **📜 Report History** tab
2. Filter by template (optional)
3. View all generated reports with:
   - Generation timestamp
   - Template used
   - Run ID
   - Format
   - Status
   - File name
   - File size

## Report Sections Explained

### Executive Summary
- High-level portfolio overview
- Key metrics at a glance
- Main insights and recommendations

### Performance Metrics
- Total return, Sharpe ratio, max drawdown
- Win rate, hit rate
- Risk-adjusted returns

### Portfolio Composition
- Current holdings
- Position weights
- Sector allocation
- Top positions

### Risk Analysis
- Risk metrics (volatility, beta, VaR)
- Drawdown analysis
- Concentration risks
- Risk warnings

### Recommendations
- AI-generated buy/sell/hold recommendations
- Target prices and stop losses
- Confidence levels
- Reasoning

### Attribution
- Performance attribution breakdown
- Factor contributions
- Sector contributions
- Stock selection effects

### Benchmark Comparison
- Comparison vs SPY, QQQ
- Alpha and beta
- Tracking error
- Up/down capture ratios

### Factor Exposure
- Market, size, value, momentum exposures
- Quality and low volatility factors
- Factor risk contributions

## Report Formats

### PDF Format
- **Best for**: Sharing, printing, presentations
- **Features**: Professional layout, charts, tables
- **Size**: Medium (typically 50-500 KB)

### Excel Format
- **Best for**: Data analysis, further processing
- **Features**: Multiple sheets, formulas, formatting
- **Size**: Medium (typically 100-1000 KB)

### CSV Format
- **Best for**: Simple data export, spreadsheet import
- **Features**: Plain text, comma-separated values
- **Size**: Small (typically 10-100 KB)

### JSON Format
- **Best for**: Programmatic access, API integration
- **Features**: Structured data, machine-readable
- **Size**: Small to medium (typically 50-500 KB)

### HTML Format
- **Best for**: Web viewing, email embedding
- **Features**: Web-friendly, interactive charts
- **Size**: Medium (typically 100-500 KB)

## Best Practices

1. **Create Multiple Templates**: Different templates for different purposes
   - Executive summary template (lightweight)
   - Full analysis template (comprehensive)
   - Risk-focused template (risk metrics only)

2. **Use Appropriate Formats**: 
   - PDF for sharing with stakeholders
   - Excel for data analysis
   - JSON for programmatic access

3. **Select Relevant Sections**: Only include sections you need
   - Reduces report size
   - Faster generation
   - Focused content

4. **Regular Generation**: Generate reports regularly for tracking
   - Monthly portfolio reports
   - Quarterly performance reviews
   - Ad-hoc analysis reports

5. **Template Naming**: Use descriptive names
   - "Monthly Executive Summary"
   - "Full Analysis Report"
   - "Risk Assessment Report"

## Troubleshooting

### Report Generation Fails

1. **Check Run Status**: Ensure run is completed
2. **Check Analysis Results**: Some sections require specific analysis results
3. **Check File Permissions**: Ensure output directory is writable
4. **Check Dependencies**: PDF/Excel generation requires additional packages

### Missing Sections in Report

1. **Check Template Configuration**: Verify sections are enabled
2. **Check Analysis Results**: Some sections require specific analysis to be run
3. **Check Run Data**: Ensure run has required data

### Large Report Files

1. **Reduce Sections**: Include only necessary sections
2. **Use CSV/JSON**: For data-only reports
3. **Check Data Size**: Large portfolios generate larger reports

### Report Format Issues

1. **PDF**: Ensure reportlab is installed
2. **Excel**: Ensure openpyxl is installed
3. **Check File Extension**: Verify correct format is selected

## API Usage

### Programmatic Template Creation

```python
from src.analytics.report_templates import ReportTemplateEngine, ReportFormat

engine = ReportTemplateEngine()

# Create template
template = engine.create_template(
    name="Monthly Report",
    format=ReportFormat.PDF.value,
    sections=[
        {'type': 'executive_summary', 'enabled': True},
        {'type': 'performance_metrics', 'enabled': True},
        {'type': 'portfolio_composition', 'enabled': True}
    ],
    description="Monthly portfolio report"
)

# Generate report
report_gen = engine.generate_report(
    template_id=template.id,
    run_id='your_run_id',
    generated_by='automated_script'
)
```

### Programmatic Report Generation

```python
from src.analytics.report_templates import ReportTemplateEngine

engine = ReportTemplateEngine()

# Get template
templates = engine.get_templates(enabled_only=True)
template = templates[0]  # Use first enabled template

# Generate report
report_gen = engine.generate_report(
    template_id=template.id,
    run_id='your_run_id'
)

if report_gen.status == 'completed':
    print(f"Report generated: {report_gen.file_path}")
```

## Scheduled Reports (Coming Soon)

Future versions will support:
- Cron-like scheduling
- Automatic report generation
- Email delivery of reports
- Report archiving

## Support

For issues or questions:
- Check the [FAQ](faq.md)
- Review [User Guide](user-guide.md)
- Check report history for generation status
