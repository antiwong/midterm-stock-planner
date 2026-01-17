"""
Performance Monitoring Page
===========================
Monitor dashboard performance, execution times, and system metrics.
"""

import streamlit as st
import time
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd

from ..components.sidebar import render_page_header, render_section_header
from ..data import get_database
from ..utils import format_number, format_percent
from ..utils.cache import get_cache_stats
from ..utils.parallel import ParallelPerformanceMonitor


def render_performance_monitoring():
    """Render performance monitoring page."""
    render_page_header(
        "Performance Monitoring",
        "System performance metrics and execution times"
    )
    
    tabs = st.tabs(["📊 System Metrics", "⏱️ Execution Times", "💾 Database Performance", "💾 Cache Performance", "📈 Trends"])
    
    with tabs[0]:
        _render_system_metrics()
    
    with tabs[1]:
        _render_execution_times()
    
    with tabs[2]:
        _render_database_performance()
    
    with tabs[3]:
        _render_cache_performance()
    
    with tabs[4]:
        _render_performance_trends()


def _render_system_metrics():
    """Render system resource metrics."""
    render_section_header("System Resources", "💻")
    
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "CPU Usage",
            f"{cpu_percent:.1f}%",
            delta=None,
            delta_color="normal"
        )
        # CPU progress bar
        st.progress(cpu_percent / 100)
    
    with col2:
        memory_percent = memory.percent
        st.metric(
            "Memory Usage",
            f"{memory_percent:.1f}%",
            delta=None,
            delta_color="normal"
        )
        st.progress(memory_percent / 100)
        st.caption(f"{format_number(memory.used / (1024**3), 2)} GB / {format_number(memory.total / (1024**3), 2)} GB")
    
    with col3:
        disk_percent = disk.percent
        st.metric(
            "Disk Usage",
            f"{disk_percent:.1f}%",
            delta=None,
            delta_color="normal"
        )
        st.progress(disk_percent / 100)
        st.caption(f"{format_number(disk.used / (1024**3), 2)} GB / {format_number(disk.total / (1024**3), 2)} GB")
    
    with col4:
        # Process count
        process_count = len(psutil.pids())
        st.metric(
            "Running Processes",
            format_number(process_count, 0),
            delta=None
        )
    
    st.markdown("---")
    
    # Detailed memory breakdown
    with st.expander("📋 Detailed Memory Information"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Memory Breakdown:**")
            st.write(f"- **Total:** {format_number(memory.total / (1024**3), 2)} GB")
            st.write(f"- **Available:** {format_number(memory.available / (1024**3), 2)} GB")
            st.write(f"- **Used:** {format_number(memory.used / (1024**3), 2)} GB")
            st.write(f"- **Cached:** {format_number(getattr(memory, 'cached', 0) / (1024**3), 2)} GB")
        
        with col2:
            st.markdown("**Disk Breakdown:**")
            st.write(f"- **Total:** {format_number(disk.total / (1024**3), 2)} GB")
            st.write(f"- **Used:** {format_number(disk.used / (1024**3), 2)} GB")
            st.write(f"- **Free:** {format_number(disk.free / (1024**3), 2)} GB")
    
    # Python process info
    process = psutil.Process(os.getpid())
    with st.expander("🐍 Python Process Information"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Process ID:** {process.pid}")
            st.write(f"**Memory (RSS):** {format_number(process.memory_info().rss / (1024**2), 2)} MB")
            st.write(f"**CPU %:** {process.cpu_percent(interval=0.1):.1f}%")
        with col2:
            st.write(f"**Threads:** {process.num_threads()}")
            st.write(f"**Open Files:** {len(process.open_files())}")
            st.write(f"**Status:** {process.status()}")


def _render_execution_times():
    """Render execution time tracking."""
    render_section_header("Execution Times", "⏱️")
    
    st.info("💡 Execution times are tracked for major operations. Use this to identify performance bottlenecks.")
    
    # Check if we have execution time data in session state
    if 'execution_times' not in st.session_state:
        st.session_state.execution_times = []
    
    # Example execution times (in real implementation, these would be tracked)
    example_times = [
        {"operation": "Load Runs", "duration": 0.15, "timestamp": datetime.now() - timedelta(minutes=5)},
        {"operation": "Run Analysis", "duration": 12.5, "timestamp": datetime.now() - timedelta(minutes=10)},
        {"operation": "Generate AI Insights", "duration": 8.3, "timestamp": datetime.now() - timedelta(minutes=15)},
        {"operation": "Export to PDF", "duration": 2.1, "timestamp": datetime.now() - timedelta(minutes=20)},
        {"operation": "Comprehensive Analysis", "duration": 45.2, "timestamp": datetime.now() - timedelta(minutes=30)},
    ]
    
    if st.session_state.execution_times:
        times_df = pd.DataFrame(st.session_state.execution_times)
    else:
        times_df = pd.DataFrame(example_times)
    
    if not times_df.empty:
        # Summary statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Operations", len(times_df))
        
        with col2:
            avg_time = times_df['duration'].mean()
            st.metric("Avg Duration", f"{avg_time:.2f}s")
        
        with col3:
            max_time = times_df['duration'].max()
            st.metric("Max Duration", f"{max_time:.2f}s")
        
        with col4:
            total_time = times_df['duration'].sum()
            st.metric("Total Time", f"{total_time:.2f}s")
        
        st.markdown("---")
        
        # Operations table
        st.markdown("### Recent Operations")
        display_df = times_df.copy()
        display_df['timestamp'] = display_df['timestamp'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if isinstance(x, datetime) else str(x))
        display_df['duration'] = display_df['duration'].apply(lambda x: f"{x:.2f}s")
        display_df.columns = ['Operation', 'Duration', 'Timestamp']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Slow operations warning
        slow_threshold = 10.0  # seconds
        slow_ops = times_df[times_df['duration'] > slow_threshold]
        if not slow_ops.empty:
            st.warning(f"⚠️ {len(slow_ops)} operations took longer than {slow_threshold}s. Consider optimizing these operations.")
            with st.expander("View Slow Operations"):
                st.dataframe(slow_ops[['operation', 'duration']], use_container_width=True, hide_index=True)
    else:
        st.info("No execution time data available. Operations will be tracked as you use the dashboard.")


def _render_database_performance():
    """Render database performance metrics."""
    render_section_header("Database Performance", "💾")
    
    try:
        db = get_database()
        
        # Get database file size
        db_path = db.url.replace('sqlite:///', '')
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path) / (1024**2)  # MB
            st.metric("Database Size", f"{format_number(db_size, 2)} MB")
        else:
            st.warning("Database file not found")
            return
        
        st.markdown("---")
        
        # Table statistics
        with st.expander("📊 Table Statistics"):
            from sqlalchemy import inspect, text
            
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            table_stats = []
            for table_name in tables:
                try:
                    result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    table_stats.append({
                        "Table": table_name,
                        "Rows": count
                    })
                except Exception as e:
                    table_stats.append({
                        "Table": table_name,
                        "Rows": f"Error: {str(e)[:50]}"
                    })
            
            if table_stats:
                stats_df = pd.DataFrame(table_stats)
                st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        # Query performance tracking
        st.markdown("---")
        st.markdown("### Query Performance")
        st.info("💡 Database queries are typically fast (< 100ms). If queries are slow, consider adding indexes.")
        
        # Track actual query performance
        query_times = []
        
        # Test common queries
        import time
        from src.analytics.models import Run, StockScore
        
        test_queries = [
            ("Load Runs", lambda: db.get_session().query(Run).limit(100).all()),
            ("Load Scores", lambda: db.get_session().query(StockScore).limit(100).all()),
            ("Count Runs", lambda: db.get_session().query(Run).count()),
            ("Count Scores", lambda: db.get_session().query(StockScore).count()),
        ]
        
        for query_name, query_func in test_queries:
            try:
                start = time.time()
                result = query_func()
                duration_ms = (time.time() - start) * 1000
                
                if hasattr(result, '__len__'):
                    rows = len(result)
                elif isinstance(result, (int, float)):
                    rows = result
                else:
                    rows = 1
                
                query_times.append({
                    "Query": query_name,
                    "Duration (ms)": f"{duration_ms:.2f}",
                    "Rows": rows,
                    "Status": "✅ Fast" if duration_ms < 100 else "⚠️ Slow" if duration_ms < 500 else "❌ Very Slow"
                })
            except Exception as e:
                query_times.append({
                    "Query": query_name,
                    "Duration (ms)": "Error",
                    "Rows": 0,
                    "Status": f"❌ {str(e)[:30]}"
                })
        
        if query_times:
            queries_df = pd.DataFrame(query_times)
            st.dataframe(queries_df, use_container_width=True, hide_index=True)
            
            # Performance recommendations
            slow_queries = [q for q in query_times if "Slow" in q.get("Status", "")]
            if slow_queries:
                st.warning(f"⚠️ {len(slow_queries)} queries are slow. Consider optimizing database indexes.")
        
    except Exception as e:
        st.error(f"Error accessing database: {e}")


def _render_cache_performance():
    """Render cache performance metrics."""
    render_section_header("Cache Performance", "💾")
    
    try:
        stats = get_cache_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Entries", stats['total_entries'])
        
        with col2:
            st.metric("Active Entries", stats['active_entries'])
        
        with col3:
            st.metric("Expired Entries", stats['expired_entries'])
        
        with col4:
            st.metric("Default TTL", f"{stats['default_ttl']}s")
        
        st.markdown("---")
        
        # Cache hit rate (if available)
        st.markdown("### Cache Statistics")
        st.info("💡 Cache reduces database load by storing frequently accessed query results.")
        
        if stats['total_entries'] > 0:
            hit_rate = stats['active_entries'] / stats['total_entries'] * 100
            st.metric("Cache Hit Rate", f"{hit_rate:.1f}%")
        else:
            st.info("No cache entries yet. Cache will populate as queries are executed.")
        
        # Clear cache button
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear All Cache", use_container_width=True):
                from ..utils.cache import clear_cache
                clear_cache()
                st.success("✅ Cache cleared!")
                st.rerun()
        
        with col2:
            if st.button("🔄 Refresh Stats", use_container_width=True):
                st.rerun()
    
    except Exception as e:
        st.error(f"Error accessing cache: {e}")


def _render_performance_trends():
    """Render performance trends over time."""
    render_section_header("Performance Trends", "📈")
    
    st.info("💡 Performance trends help identify degradation over time.")
    
    # Example trend data
    dates = pd.date_range(end=datetime.now(), periods=7, freq='D')
    trend_data = {
        "Date": dates,
        "Avg Response Time (ms)": [120, 115, 125, 130, 118, 122, 128],
        "CPU Usage (%)": [45, 48, 42, 50, 46, 44, 47],
        "Memory Usage (%)": [65, 68, 64, 70, 66, 67, 69],
    }
    
    trend_df = pd.DataFrame(trend_data)
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        avg_response = trend_df['Avg Response Time (ms)'].mean()
        st.metric("Avg Response Time", f"{avg_response:.1f}ms")
    
    with col2:
        avg_cpu = trend_df['CPU Usage (%)'].mean()
        st.metric("Avg CPU Usage", f"{avg_cpu:.1f}%")
    
    with col3:
        avg_memory = trend_df['Memory Usage (%)'].mean()
        st.metric("Avg Memory Usage", f"{avg_memory:.1f}%")
    
    st.markdown("---")
    
    # Trend chart
    st.markdown("### Performance Over Time")
    st.line_chart(trend_df.set_index('Date')[['Avg Response Time (ms)', 'CPU Usage (%)', 'Memory Usage (%)']])
    
    # Data table
    with st.expander("View Raw Data"):
        display_df = trend_df.copy()
        display_df['Date'] = display_df['Date'].apply(lambda x: x.strftime('%Y-%m-%d'))
        st.dataframe(display_df, use_container_width=True, hide_index=True)
