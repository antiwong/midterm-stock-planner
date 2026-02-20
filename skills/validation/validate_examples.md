# Validate Examples Skill

## Purpose

Ensure that code examples embedded in documentation are accurate, runnable, and produce expected results. This prevents documentation drift where examples become outdated or incorrect as the codebase evolves.

## Prerequisites

- Documentation files with code examples created (Markdown format)
- Working environment with required dependencies installed
- Access to the codebase that examples reference
- Test data or fixtures needed to run examples

## Process

### 1. Extract Code Examples from Documentation

Extract all code blocks from markdown files:
- Identify fenced code blocks (```language)
- Filter for relevant languages (python, javascript, shell, etc.)
- Preserve example labels and context
- Map examples to their source documentation

```bash
# Extract examples from markdown file
grep -A 50 "^\\`\\`\\`" documentation.md | grep -B 50 "^\\`\\`\\`"
```

### 2. Prepare Test Environment

Set up isolated test context:
- Create temporary test directory
- Copy or link necessary modules/files
- Ensure imports can resolve correctly
- Install required test dependencies

### 3. Execute Code Examples

Run each extracted example:
- Execute in isolated Python/Node/Shell environment
- Capture stdout and stderr output
- Record execution time
- Capture any exceptions or errors
- Track success/failure status

### 4. Validate Output

Compare actual output with expected results:
- Extract expected output from documentation (comments or explicit sections)
- Perform exact string match or pattern matching as appropriate
- Check for warnings or deprecation notices
- Verify performance characteristics if specified

### 5. Generate Validation Report

Create a comprehensive report:
- Total examples tested
- Pass/fail counts and percentages
- List of failing examples with error details
- Suggestions for fixes
- Links back to source documentation

## Outputs

### Validation Report

```
Example Validation Report
========================

Documentation: scene.md
Total Examples: 15
Passed: 14 (93%)
Failed: 1 (7%)

Passed Examples:
  ✓ Creating a basic scene
  ✓ Adding objects to scene
  ✓ Rendering with camera
  ✓ Updating object properties
  [... more examples ...]

Failed Examples:
  ✗ Advanced scene composition
    Error: AttributeError: 'Scene' object has no attribute 'compose'
    Line: 42
    Expected output: "Composition complete"
    Actual output: "AttributeError: 'Scene' object has no attribute 'compose'"

Recommendations:
  - Update scene.md line 42: 'compose' method may have been renamed
  - Check Scene API reference for current method names
```

## Examples

### Test Examples from scene.md API Reference

#### Example 1: Creating a Basic Scene

**Documentation Extract:**
```python
from scene import Scene

# Create a new scene
scene = Scene(width=1920, height=1080)
print(scene.dimensions)
```

**Expected Output:**
```
(1920, 1080)
```

**Test Process:**
1. Extract code from markdown
2. Create temporary Python file
3. Execute: `python test_example_1.py`
4. Verify output matches `(1920, 1080)`
5. Record as PASS/FAIL

#### Example 2: Adding Objects to Scene

**Documentation Extract:**
```python
from scene import Scene, Object

scene = Scene()
obj = Object(name="cube", type="mesh")
scene.add_object(obj)
print(f"Objects in scene: {len(scene.objects)}")
```

**Expected Output:**
```
Objects in scene: 1
```

#### Example 3: Rendering with Camera

**Documentation Extract:**
```python
from scene import Scene, Camera

scene = Scene()
camera = Camera(position=(0, 0, 10))
scene.set_camera(camera)
output = scene.render()
print(f"Rendered: {output is not None}")
```

**Expected Output:**
```
Rendered: True
```

## Validation Checklist

- [ ] All code examples are extracted from documentation
- [ ] Test environment is properly configured
- [ ] Each example runs without syntax errors
- [ ] No ImportError or ModuleNotFoundError occurs
- [ ] Actual output matches expected output exactly
- [ ] No deprecation warnings in critical examples
- [ ] All examples complete within reasonable time (<5 seconds each)
- [ ] Failed examples have clear error messages
- [ ] Report identifies which documentation needs updates
- [ ] Report is saved to version control (examples_validation_report.txt)
- [ ] CI/CD pipeline runs validation on documentation changes
- [ ] Examples use realistic, production-relevant scenarios

## Related Skills

- [Document Code](./document_code.md) - Creating documentation with examples
- [Code Review](./code_review.md) - Reviewing implementation against specifications
- [Test Coverage](./test_coverage.md) - Measuring test coverage for code

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors in examples | Verify module paths and ensure dependencies are installed |
| Output mismatch | Check if API has changed; update documentation or example |
| Timeout on execution | Simplify example or add timeout handling |
| Missing test data | Create fixtures or provide sample data files |
| Environment differences | Use containerized test environment for consistency |

## Notes

- Run validation regularly (on every documentation update or release)
- Keep examples simple and focused on single concepts
- Include comments explaining what output to expect
- Update examples when API changes
- Consider adding example tags in markdown for easier extraction
