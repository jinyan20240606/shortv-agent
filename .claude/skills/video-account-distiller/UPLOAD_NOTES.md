# Upload Notes

Upload this entire folder to WorkBuddy:

```text
workbuddy_douyin_video_skill
```

Do not add `.env`, cookies, downloaded videos, transcripts, or outputs to the upload package.

After upload, first run:

```powershell
cd scripts
python install_minimal.py
```

Do not run `npm install`. The upload package includes only the minimal Node dependency needed by the signer.

Then use:

```powershell
python llmagent_video\prepare_video_for_workbuddy.py "抖音或视频号链接" --requirement "你的脚本要求"
```

Create an IP style profile:

```powershell
python llmagent_video\create_ip_profile.py --name "panjie" --text-file "corpus.txt" --docx-file "corpus.docx" --account-url "DOUYIN_USER_URL"
```

Use that profile:

```powershell
python llmagent_video\prepare_video_for_workbuddy.py "抖音或视频号链接" --requirement "你的脚本要求" --profile "panjie"
```
