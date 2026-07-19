# LLMAgent Video

This folder supports three separate WorkBuddy flows.

## Flow A: Video HTML Report

Input: one Douyin video link.

Output shown to the user: one final HTML report.

```powershell
python .\llmagent_video\prepare_video_for_workbuddy.py "DOUYIN_VIDEO_URL" --requirement "USER_REQUIREMENT"
python .\llmagent_video\finalize_video_report.py --material "MATERIAL_JSON" --result-file "FINAL_OUTPUT.md" --output "WORK_ID_final_report.html"
```

Use `--profile "PROFILE_NAME"` only when the user selects a saved IP style.

## Flow B: IP Style Profile

Input: a Douyin account homepage, `.docx`/`.txt` corpus, pasted corpus, or both.

Output shown to the user: saved profile summary.

```powershell
python .\llmagent_video\list_ip_profiles.py
python .\llmagent_video\create_ip_profile.py --name "PROFILE_NAME" --account-url "DOUYIN_USER_URL"
python .\llmagent_video\create_ip_profile.py --name "PROFILE_NAME" --docx-file "CORPUS.docx"
```

Profiles are saved under:

```text
llmagent_video/profiles
```

## Flow C: Account Analysis

Input: one Douyin user homepage.

Output shown to the user: concise account analysis. Ask whether to save this account as an IP style.

```powershell
python .\llmagent_video\track_account.py "DOUYIN_USER_URL" --max-works 30
```

Do not export Excel unless the user explicitly asks for it.

## Notes

- If no Douyin cookie exists, the auth flow opens Edge/Chrome automatically.
- The package bundles the minimal Node signer dependency. Do not run `npm install`.
- The final customer-facing video deliverable should be HTML only.
