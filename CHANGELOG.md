# Changelog

All notable changes to this project will be documented in this file. See [Conventional Commits](https://conventionalcommits.org) for commit guidelines.

## [4.1.1](https://github.com/fabricekrebs/magictoolbox/compare/v4.1.0...v4.1.1) (2025-12-18)

### Bug Fixes

* **ci:** manually capture semantic-release version outputs ([5dbcfda](https://github.com/fabricekrebs/magictoolbox/commit/5dbcfda91f089c9bdf5244b03fbc0e1157f73aee))

## [4.1.0](https://github.com/fabricekrebs/magictoolbox/compare/v4.0.0...v4.1.0) (2025-12-18)

### Features

* **ci:** combine release and deployment into single workflow ([a29a4cb](https://github.com/fabricekrebs/magictoolbox/commit/a29a4cbf31422881170184b43bab017afd1a5076))

### Bug Fixes

* **ci:** allow build job to run when release is skipped ([3853ea0](https://github.com/fabricekrebs/magictoolbox/commit/3853ea0bdb865c904d5de75c4178e4a3be22d8cf))
* **ci:** correct YAML syntax error in deploy-prod job ([741b210](https://github.com/fabricekrebs/magictoolbox/commit/741b210f4a78adce4af2414641da3c6dd442ae9c))
* **ci:** remove duplicate keys in deploy-prod job ([0bf10e0](https://github.com/fabricekrebs/magictoolbox/commit/0bf10e05868827f5407bbb9db92c26bb1ce26ce4))

## [4.0.0](https://github.com/fabricekrebs/magictoolbox/compare/v3.0.1...v4.0.0) (2025-12-18)

### ⚠ BREAKING CHANGES

* **ci:** Production deployments now triggered by semantic version tags instead of direct main branch pushes

* fix(ci): disable GitHub plugin PR/issue comments to prevent 404 errors

* feat(ci): trigger deployment workflow after semantic release

* fix(ci): correct azure-deploy workflow YAML syntax

* fix(ci): use semantic-release action to properly set outputs

### Bug Fixes

* **ci:** use semantic-release action to properly set outputs ([#6](https://github.com/fabricekrebs/magictoolbox/issues/6)) ([11905f8](https://github.com/fabricekrebs/magictoolbox/commit/11905f8996343d63733b2935a8eaf1fd377b8484))

## [3.0.1](https://github.com/fabricekrebs/magictoolbox/compare/v3.0.0...v3.0.1) (2025-12-18)

### Bug Fixes

* **ci:** correct azure-deploy workflow YAML syntax ([928b5be](https://github.com/fabricekrebs/magictoolbox/commit/928b5be5da8439244848a07c2ac70dd4813a6849))

## [3.0.0](https://github.com/fabricekrebs/magictoolbox/compare/v2.0.0...v3.0.0) (2025-12-18)

### ⚠ BREAKING CHANGES

* **ci:** Production deployments now triggered by semantic version tags instead of direct main branch pushes

* fix(ci): disable GitHub plugin PR/issue comments to prevent 404 errors

* feat(ci): trigger deployment workflow after semantic release

### Features

* **ci:** trigger deployment workflow after semantic release ([#4](https://github.com/fabricekrebs/magictoolbox/issues/4)) ([419f9be](https://github.com/fabricekrebs/magictoolbox/commit/419f9be8a3f4069c48de5a2ab3f633ba490a5990))

## [2.0.0](https://github.com/fabricekrebs/magictoolbox/compare/v1.0.0...v2.0.0) (2025-12-18)

### ⚠ BREAKING CHANGES

* **ci:** Production deployments now triggered by semantic version tags instead of direct main branch pushes

* fix(ci): disable GitHub plugin PR/issue comments to prevent 404 errors

### Bug Fixes

* **ci:** disable GitHub plugin PR/issue comments ([#3](https://github.com/fabricekrebs/magictoolbox/issues/3)) ([1ab3b14](https://github.com/fabricekrebs/magictoolbox/commit/1ab3b147f546997358b188b95cac3bc303dd6ca0))

## [1.0.0](https://github.com/fabricekrebs/magictoolbox/compare/v0.0.1...v1.0.0) (2025-12-18)

### ⚠ BREAKING CHANGES

* **ci:** Production deployments now triggered by semantic version tags instead of direct main branch pushes
* Migrated from generic containers to tool-specific containers

## Changes

### Infrastructure (Phase 1)
- Added tool-specific containers in storage.bicep:
  - pdf-uploads / pdf-processed
  - image-uploads / image-processed
  - gpx-uploads / gpx-processed
  - video-uploads / video-processed (already existed)
  - ocr-uploads / ocr-processed
- Deprecated generic 'uploads' and 'processed' containers

### Azure Functions (Phase 2)
- Updated all functions to use tool-specific containers
- Simplified blob paths (removed subdirectories)
- Functions: video/rotate, pdf/convert, gpx/convert, image/convert, gpx/speed, image/ocr, gpx/merge

### Django Tools (Phase 3)
- Updated all tool plugins to use tool-specific containers
- Simplified blob naming (no subdirectories)
- Tools: PDF converter, image converter, GPX converter, GPX merger, GPX speed modifier, video rotation, OCR tool

### Configuration Cleanup (Phase 4)
- Removed AZURE_ACCOUNT_NAME duplicate variable
- Standardized on AZURE_STORAGE_ACCOUNT_NAME
- Updated Django settings (base.py, production.py)
- Updated .env.example
- Removed fallback logic from tools

## Benefits
- Better security isolation per tool
- Independent lifecycle policies
- Clearer organization
- Simplified cost tracking
- Prevents cross-tool naming conflicts

## Migration Path
1. Deploy infrastructure to create new containers
2. Deploy Azure Functions with updated container logic
3. Deploy Django app with updated tool logic
4. Test each tool end-to-end
5. Remove deprecated containers after verification

See documentation/NAMING_CONSISTENCY_AUDIT.md for full details.

### Features

* add 5-second history polling to all async tools ([8841a61](https://github.com/fabricekrebs/magictoolbox/commit/8841a61e9175c35a37005be6f43d84195cd050a5))
* add admin cleanup tool to troubleshooting page ([9156e3e](https://github.com/fabricekrebs/magictoolbox/commit/9156e3ee29fce5575aefef675155b155a516d620))
* add Azure Functions HTTP triggers and troubleshooting page ([2075a1b](https://github.com/fabricekrebs/magictoolbox/commit/2075a1b54ccdccc04fb674f8c4375497c3e01980))
* Add three new tools - Base64 encoder/decoder, EXIF extractor, and OCR text extraction ([ab2aa07](https://github.com/fabricekrebs/magictoolbox/commit/ab2aa077c3dbcaf9e4029637e8634ca033aeee89))
* **api:** add DELETE endpoint for execution history ([f085791](https://github.com/fabricekrebs/magictoolbox/commit/f08579116fa7e61f21658fc609fb91b84ce17655))
* **ci:** implement automatic semantic versioning and deployment ([ce7286a](https://github.com/fabricekrebs/magictoolbox/commit/ce7286ab15e3f794f6c5616cd38f09dc88804848))
* establish async file processing gold standard and simplify configuration ([5b71a03](https://github.com/fabricekrebs/magictoolbox/commit/5b71a031759433dbd44dfd0f12c33c491de87f37))
* **frontend:** add search filter and inline icons to history sidebar ([d8ca80b](https://github.com/fabricekrebs/magictoolbox/commit/d8ca80b73b2b03ce46140dc75bf9c8721eec346f))
* **frontend:** add shared history management module and CSS ([5442f90](https://github.com/fabricekrebs/magictoolbox/commit/5442f900f84025d09f53bffb0508e6d9b54af3b9))
* **frontend:** implement gold standard layout for PDF converter ([3f29385](https://github.com/fabricekrebs/magictoolbox/commit/3f29385b745434c949c9769f280310bf67180f9d))
* **frontend:** implement gold standard layout for video rotation ([f4cf64f](https://github.com/fabricekrebs/magictoolbox/commit/f4cf64f80ee1f7534b73df81378b4d1a07eaf0d3))
* **frontend:** move action buttons inline with status ([dd1396e](https://github.com/fabricekrebs/magictoolbox/commit/dd1396ea7f6722d1df9afc61758f6c10e7d4807f))
* implement tool-specific blob storage containers ([69bc1a2](https://github.com/fabricekrebs/magictoolbox/commit/69bc1a2c5fbb593088b671ec1f84542dd59eb230))
* preserve original filenames in conversion tools ([0efdf0b](https://github.com/fabricekrebs/magictoolbox/commit/0efdf0beb1838a262b072af81e102915f48c14a0))
* **tests:** comprehensive E2E API tests for all 11 tools ([ae413e7](https://github.com/fabricekrebs/magictoolbox/commit/ae413e7237d4e4eefae5ccf1ea78067f97c020cf))
* **tests:** use real sample files for video and image tests ([edc3a14](https://github.com/fabricekrebs/magictoolbox/commit/edc3a1436955a9998b271231e1db6023b04c153c))
* **tools:** add GPX Merger tool with async processing ([16379d3](https://github.com/fabricekrebs/magictoolbox/commit/16379d3d2e64fa5685ed35d75398824ab1b3cac6))
* **tools:** convert image, GPX-KML, GPX-speed tools to async pattern ([deb82da](https://github.com/fabricekrebs/magictoolbox/commit/deb82dad2daf7eec8f123f00d9afd91e4c29546b))
* **tools:** improve async tool UX with real-time updates and progress tracking ([db9b02a](https://github.com/fabricekrebs/magictoolbox/commit/db9b02a1ee4e2b88b8a178e0c7956ce42c5cf4b7))

### Bug Fixes

* add italynorth location abbreviation to all Bicep modules ([656fc2a](https://github.com/fabricekrebs/magictoolbox/commit/656fc2aa01598c8e6460ffb43e67fa73d91809dc))
* add main branch trigger for infrastructure deployment ([f85dbcb](https://github.com/fabricekrebs/magictoolbox/commit/f85dbcbb796f0188a792119d552c7dd0ff57b057))
* add missing parameters to Azure Function HTTP payloads ([697b614](https://github.com/fabricekrebs/magictoolbox/commit/697b6144308b95fd9d870e1a439c2bed09ce09c6))
* add null checks to prevent DOM manipulation errors in async tools ([ea48872](https://github.com/fabricekrebs/magictoolbox/commit/ea48872b89074384c0e72ee705a2426a9eb269a4))
* **ci:** handle Flex Consumption deployment health check gracefully ([5b054b1](https://github.com/fabricekrebs/magictoolbox/commit/5b054b119796007afa95226f71b67aacd0862fe7))
* **ci:** simplify Flex Consumption deployment validation ([0f889f4](https://github.com/fabricekrebs/magictoolbox/commit/0f889f4cc35371c79090d2273c74d9361323b078))
* **ci:** use ZIP deployment for Flex Consumption Function App ([bcb7a12](https://github.com/fabricekrebs/magictoolbox/commit/bcb7a12f0544dbeeed621e909b41751f0fd8d509))
* correct blob container names for async tools ([9884411](https://github.com/fabricekrebs/magictoolbox/commit/988441134529cf994fd05e211bf6f6114cd3e083))
* correct download functionality for all file conversion tools ([00bbd4f](https://github.com/fabricekrebs/magictoolbox/commit/00bbd4f7ca6a62f7e4a583a133ef68ee6fc687c9))
* **deployment:** include pre-built dependencies in Function App deployment ([6f7d5fb](https://github.com/fabricekrebs/magictoolbox/commit/6f7d5fbd07656abd41dc37462b95e482af0790f9))
* disable soft delete for blobs/containers and change storage account suffix to 02 ([e364798](https://github.com/fabricekrebs/magictoolbox/commit/e3647983c142252d64bc647935e7d1b48b091871))
* ensure download buttons in history section work reliably ([315db9e](https://github.com/fabricekrebs/magictoolbox/commit/315db9ef711997bd797670c6642ed5f8a2aad9a8))
* **frontend:** fix history sidebar not loading and remove My Conversions button ([a4d2f33](https://github.com/fabricekrebs/magictoolbox/commit/a4d2f332bdfe636662eee2f6a037374c656ff717))
* **functions:** simplify to minimal working set (health, video rotation, GPX conversion) ([e7a9c5d](https://github.com/fabricekrebs/magictoolbox/commit/e7a9c5d75f9fae49f76d239da6ece68415239f91))
* **gpx-merger:** add missing cleanup() method to satisfy BaseTool abstract class ([10cf89f](https://github.com/fabricekrebs/magictoolbox/commit/10cf89f123311ae8d4aa7c809377f35d51b571e9))
* **gpx-speed-modifier:** wrap JS in DOMContentLoaded to prevent null element errors ([35762d9](https://github.com/fabricekrebs/magictoolbox/commit/35762d9eec98de5ca7beea3b86c7dd1d3ea06338))
* **image-converter:** fix download button not working ([f42e949](https://github.com/fabricekrebs/magictoolbox/commit/f42e949dca68627e0e72fd108eecaf5d61d486d6))
* **infra:** add missing Azure Functions runtime settings ([ff56295](https://github.com/fabricekrebs/magictoolbox/commit/ff56295c1b77456c09e1f5d1c7027acc60830afc))
* **infra:** add runtime app settings for Python v2 worker indexing ([b809771](https://github.com/fabricekrebs/magictoolbox/commit/b8097715bfdac7cf0c5669c354f3d75ca302123e))
* **infra:** correct Azure Function base URL configuration ([ca1166a](https://github.com/fabricekrebs/magictoolbox/commit/ca1166ad3a4726424b4cad8bff062c945a8c3b4d))
* **infra:** Fix Redis connection with proper authentication in Container Apps ([bf40324](https://github.com/fabricekrebs/magictoolbox/commit/bf40324f2e5073a0cdddf4aaec2f1035af929fbc))
* **infra:** remove conflicting runtime settings for Flex Consumption plan ([360b60c](https://github.com/fabricekrebs/magictoolbox/commit/360b60c0f6f318d5ff76626e98cd7d91354f7e0b))
* JPG conversion format and add completed_at for image converter ([b033949](https://github.com/fabricekrebs/magictoolbox/commit/b03394983f211a749862eb7718dd10bd1ad8bb44))
* **ocr-tool:** fix history, download, and result display ([6f2985b](https://github.com/fabricekrebs/magictoolbox/commit/6f2985ba51fd3de90b81adc8e27de46989f3ffb7))
* **ocr-tool:** use correct API endpoint /convert/ instead of /extract/ ([c6c2e0b](https://github.com/fabricekrebs/magictoolbox/commit/c6c2e0b99325f53f4176109fe9f700d20cd67c38))
* **ocr:** replace pytesseract with EasyOCR to avoid system dependencies ([fea1dd0](https://github.com/fabricekrebs/magictoolbox/commit/fea1dd0108b00279640b8e8794b5169b14000d25))
* **ocr:** switch to PaddleOCR - smaller than EasyOCR ([448a492](https://github.com/fabricekrebs/magictoolbox/commit/448a49249bd70c7a9bc01e4a427c179d7ebeb444))
* properly set environment name for GitHub protection rules ([75e7976](https://github.com/fabricekrebs/magictoolbox/commit/75e7976f918af8b89cdf8849b8be0a79252c934c))
* remove remaining Redis environment variables from container-apps ([702b8f1](https://github.com/fabricekrebs/magictoolbox/commit/702b8f13d37bca3ff7289db883e609a20f8e545d))
* shorten storage account name with 'in' abbreviation for italynorth and revert to suffix 01 ([7c3add5](https://github.com/fabricekrebs/magictoolbox/commit/7c3add53b16b6b45ffaa42170acf08ccafe7bdf0))
* **templates:** remove escaped backticks and dollar signs in JS template literals ([0cb15af](https://github.com/fabricekrebs/magictoolbox/commit/0cb15af980c721d39a804f58b499c2d291ccf2f3))
* **tests:** correct test parameters for video rotation and base64 encoder ([2caf4d0](https://github.com/fabricekrebs/magictoolbox/commit/2caf4d0ad74b70ca193a89808db33b1e5b952f40))
* **tests:** sync tools now return JSON files instead of dicts ([6aebae8](https://github.com/fabricekrebs/magictoolbox/commit/6aebae8c2030b996a9be1f000a9e8c4bacbdd631))
* **tests:** use correct parameter format for base64 encoder ([162160a](https://github.com/fabricekrebs/magictoolbox/commit/162160ae6f5bf6de7a5325351997a2d252686657))
* **tests:** use correct sample file key for EXIF extractor test ([39ed711](https://github.com/fabricekrebs/magictoolbox/commit/39ed71147f636ff4ca044d7edef2f47fc75619b7))
* **tools:** add null checks in video rotation selectVideo function ([de5bf93](https://github.com/fabricekrebs/magictoolbox/commit/de5bf93b53b96694436ce7f165d04ea831aca66f))
* **tools:** convert Base64 and EXIF tools to pure JavaScript ([607521c](https://github.com/fabricekrebs/magictoolbox/commit/607521cc7f37dd635db1b49016cd849bbc73d86d)), closes [#404](https://github.com/fabricekrebs/magictoolbox/issues/404)
* **tools:** correct API endpoint and add async support for new tools ([701e8ab](https://github.com/fabricekrebs/magictoolbox/commit/701e8abb20d2fa35d3fe04b2adfc6127d4c3d88c))
* use Production environment for prod deployments ([e9e9ab3](https://github.com/fabricekrebs/magictoolbox/commit/e9e9ab35a60c988fa86f60c2884a16316384a5e5))
* use same PostgreSQL SKU for dev and prod ([12460b7](https://github.com/fabricekrebs/magictoolbox/commit/12460b7680550649b43328a2399a8d58f8de8ed3))

### Documentation

* add comprehensive architecture and infrastructure diagrams to README ([9656d45](https://github.com/fabricekrebs/magictoolbox/commit/9656d45e1bd7dc919a2f0b206963f2dc1b930715))
* add comprehensive E2E API test results documentation ([9664e39](https://github.com/fabricekrebs/magictoolbox/commit/9664e3909103354aea820a69997b02ec2226077c))
* add frontend implementation guide for history sidebar ([727fdef](https://github.com/fabricekrebs/magictoolbox/commit/727fdef221957ea435256dd572b55cc980f6b299))
* add Redis removal migration documentation and auto-migration ([b59feb6](https://github.com/fabricekrebs/magictoolbox/commit/b59feb6f9348bd4dca4c7f4ca28a32dd737e1925))
* consolidate and simplify documentation ([a4df707](https://github.com/fabricekrebs/magictoolbox/commit/a4df707c394e04c5d1594cf90afa88ba5e051c9e))
* update gold standard with comprehensive frontend structure ([ecdb6c2](https://github.com/fabricekrebs/magictoolbox/commit/ecdb6c26d5a1cebbf87decab944f85992e9c94d2))

### Code Refactoring

* remove Redis, migrate to database-backed sessions and cache ([98bd34d](https://github.com/fabricekrebs/magictoolbox/commit/98bd34d15fdcb7086c406bf4f001db1c47d6d850))
* use managed identity for ACR authentication ([2b76bb0](https://github.com/fabricekrebs/magictoolbox/commit/2b76bb0b5885a40a0db3f9e1abdd28a89997ce94))
