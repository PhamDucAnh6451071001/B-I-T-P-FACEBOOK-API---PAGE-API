param(
    [string]$PageId = "1042333095638842",
    [string]$AppSecret = $env:FB_APP_SECRET
)

if (-not $AppSecret) {
    Get-Content "$PSScriptRoot\..\.env" | ForEach-Object {
        if ($_ -match '^\s*FB_APP_SECRET=(.*)$') {
            $AppSecret = $matches[1].Trim()
        }
    }
}

if (-not $AppSecret) {
    Write-Error "FB_APP_SECRET chua duoc cau hinh trong .env"
    exit 1
}

function Send-WebhookPayload {
    param(
        [string]$Label,
        [string]$JsonBody
    )

    $bodyBytes = [Text.Encoding]::UTF8.GetBytes($JsonBody)
    $hmac = New-Object System.Security.Cryptography.HMACSHA256
    $hmac.Key = [Text.Encoding]::UTF8.GetBytes($AppSecret)
    $hash = ($hmac.ComputeHash($bodyBytes) | ForEach-Object { $_.ToString("x2") }) -join ""
    $sig = "sha256=$hash"

    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllBytes($tempFile, $bodyBytes)
        Write-Host "`n=== $Label ==="
        curl.exe -i -X POST "http://localhost:3001/webhook" `
            -H "Content-Type: application/json" `
            -H "x-hub-signature-256: $sig" `
            --data-binary "@$tempFile"
    }
    finally {
        Remove-Item -Force $tempFile -ErrorAction SilentlyContinue
    }
}

$commentBody = (@{
    object = "page"
    entry  = @(@{
            id      = $PageId
            changes = @(@{
                    field = "feed"
                    value = @{
                        verb         = "add"
                        created_time = 1710000101
                        post_id      = "post_test_comment"
                        comment_id   = "cmt_test_comment"
                        message      = "Shop oi gia bao nhieu"
                        from         = @{ id = "user_comment_001" }
                    }
                })
        })
} | ConvertTo-Json -Depth 10 -Compress)

$messageBody = (@{
    object = "page"
    entry  = @(@{
            id        = $PageId
            messaging = @(@{
                    sender    = @{ id = "user_message_001" }
                    recipient = @{ id = $PageId }
                    timestamp = 1710000102
                    message   = @{ mid = "m_test_001"; text = "Shop co ship khong" }
                })
        })
} | ConvertTo-Json -Depth 10 -Compress)

Send-WebhookPayload -Label "Comment webhook" -JsonBody $commentBody
Send-WebhookPayload -Label "Messenger webhook" -JsonBody $messageBody

Write-Host "`nKiem tra raw_events:"
docker exec fb_api-kafka kafka-console-consumer --topic raw_events --from-beginning --bootstrap-server localhost:9092 --timeout-ms 5000
