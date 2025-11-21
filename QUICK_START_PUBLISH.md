# 🚀 QUICK START - DocVault v2.2.0 Publishing

**Copy & Paste Commands for Publishing**

---

## 📦 Build Status

```bash
cd z:\code\doc_vault

# Verify build artifacts
dir dist\

# Expected output:
# docvault_sdk-2.2.0.tar.gz
# docvault_sdk-2.2.0-py3-none-any.whl
```

✅ **Build Status:** READY ✅

---

## 🚀 STEP 1: Publish to PyPI (2 minutes)

### Option A: Using Config File (Recommended)

```bash
# Install twine
pip install twine

# Create ~/.pypirc (Linux/Mac) or %APPDATA%\pip\pip.ini (Windows)
# Add your PyPI API token from: https://pypi.org/manage/account/tokens/

# Upload
cd z:\code\doc_vault
twine upload dist/*
```

### Option B: Using Command Line Argument

```bash
pip install twine
cd z:\code\doc_vault

# Replace YOUR_TOKEN with your actual PyPI API token
twine upload dist/* -u __token__ -p pypi-YOUR_TOKEN
```

**Expected Output:**
```
Uploading docvault_sdk-2.2.0.tar.gz
Uploading docvault_sdk-2.2.0-py3-none-any.whl
Uploaded docvault_sdk to PyPI
```

✅ **Verify:** https://pypi.org/project/docvault-sdk/2.2.0/

---

## 🏷️ STEP 2: Create GitHub Release (5 minutes)

### Option A: Using GitHub CLI (Recommended)

```bash
# Install GitHub CLI: https://cli.github.com/

cd z:\code\doc_vault

gh release create v2.2.0 \
  --repo Ganzzi/doc-vault \
  --title "v2.2.0: Type Safety & Response Models Release" \
  --notes-file GITHUB_RELEASE_FORM.md \
  dist/docvault_sdk-2.2.0.tar.gz \
  dist/docvault_sdk-2.2.0-py3-none-any.whl
```

### Option B: Using Web UI

1. Go to: https://github.com/Ganzzi/doc-vault/releases
2. Click "Create a new release"
3. Tag: `v2.2.0`
4. Title: `v2.2.0: Type Safety & Response Models Release`
5. Description: Copy from [GITHUB_RELEASE_FORM.md](GITHUB_RELEASE_FORM.md)
6. Upload files:
   - `dist/docvault_sdk-2.2.0.tar.gz`
   - `dist/docvault_sdk-2.2.0-py3-none-any.whl`
7. Check "Set as latest release"
8. Click "Publish release"

✅ **Verify:** https://github.com/Ganzzi/doc-vault/releases/tag/v2.2.0

---

## ✅ STEP 3: Verify Installation (1 minute)

```bash
# Test installation
pip install --upgrade docvault-sdk==2.2.0

# Verify version
python -c "import doc_vault; print(doc_vault.__version__)"
# Output should be: 2.2.0

# Test import
python -c "from doc_vault import DocVaultSDK; print('✅ Success!')"
```

---

## 📊 What's Being Released

| Component | Version |
|-----------|---------|
| **PyPI Package** | docvault-sdk 2.2.0 |
| **Source File** | docvault_sdk-2.2.0.tar.gz |
| **Wheel File** | docvault_sdk-2.2.0-py3-none-any.whl |
| **Git Tag** | v2.2.0 |
| **Python Support** | 3.10, 3.11, 3.12+ |

---

## 🎯 Release Highlights

### Type Safety (v2.2)
✅ Pydantic response models  
✅ Smart string upload detection  
✅ 100% mypy validation  

### Security (v2.1)
✅ Permission viewing restricted to owners  
✅ Type-safe PermissionGrant model  
✅ Enhanced documentation  

### Architecture (v2.0)
✅ UUID-based entities  
✅ Hierarchical documents  
✅ Enhanced permissions API  

---

## 📚 Documentation Files

- **RELEASE_SUMMARY.md** - Comprehensive release guide
- **PUBLISH_INSTRUCTIONS.md** - Detailed PyPI instructions
- **GITHUB_RELEASE_FORM.md** - Release notes & form data
- **CHANGELOG.md** - Full version history
- **docs/MIGRATION_*.md** - Migration guides

---

## ⚠️ Important Notes

### PyPI API Token
- Get token: https://pypi.org/manage/account/tokens/
- Never commit to Git
- Never share publicly
- Use as password with username `__token__`

### GitHub Permissions
- Need: Maintainer or Owner role
- Check: https://github.com/Ganzzi/doc-vault/settings/access

### Timing
- PyPI indexing: 1-2 minutes
- GitHub: Immediate
- Total time: ~10 minutes

---

## 🔄 If Something Goes Wrong

### PyPI Issues
```bash
# Check status
pip index versions docvault-sdk

# Reinstall locally
pip install --force-reinstall --no-cache-dir docvault-sdk==2.2.0

# See full logs
twine upload dist/* --verbose
```

### GitHub Issues
```bash
# Delete release (before publish)
git tag -d v2.2.0
git push origin :refs/tags/v2.2.0

# Or create patch release
git tag v2.2.0-patch1
git push origin v2.2.0-patch1
```

---

## ✅ Final Checklist

- [ ] Read RELEASE_SUMMARY.md
- [ ] Have PyPI API token ready
- [ ] Verified build artifacts: `dir dist\`
- [ ] Ready to run twine upload
- [ ] GitHub account has permissions
- [ ] 10 minutes available

---

## 🎉 You're Ready!

Run the commands above in order:
1. **STEP 1:** PyPI upload (twine)
2. **STEP 2:** GitHub release
3. **STEP 3:** Verify installation

**Total Time:** ~10 minutes  
**Complexity:** Low  
**Risk:** Very low (PyPI allows version updates)

---

**For detailed help, see PUBLISH_INSTRUCTIONS.md**

Good luck! 🚀
