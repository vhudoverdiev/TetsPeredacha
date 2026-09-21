$ErrorActionPreference='Stop'
$root=(Get-Location).Path
function RGB($r,$g,$b){return [int]($r+256*$g+65536*$b)}
$ink=RGB 24 44 39
$green=RGB 66 112 29
$muted=RGB 100 115 105
$white=RGB 255 255 255
$bg=RGB 248 250 246
$pale=RGB 232 241 218
$lime=RGB 164 219 64
$app=New-Object -ComObject PowerPoint.Application
$deck=$app.Presentations.Open((Join-Path $root 'output/pptx/CRM_Peredacha_Visual_Guide_Final3.pptx'),$true,$false,$false)
$s=$deck.Slides.Item(1)
for($i=$s.Shapes.Count;$i -ge 1;$i--){if($s.Shapes.Item($i).Type -ne 13){$s.Shapes.Item($i).Delete()}}
function Box($x,$y,$w,$h,$color){$q=$s.Shapes.AddShape(1,$x,$y,$w,$h);$q.Fill.ForeColor.RGB=$color;$q.Line.Visible=0;return $q}
function Txt($str,$x,$y,$w,$h,$size,$color,$bold=$false){
 $q=$s.Shapes.AddTextbox(1,$x,$y,$w,$h)
 $q.TextFrame.MarginLeft=0;$q.TextFrame.MarginRight=0;$q.TextFrame.MarginTop=0;$q.TextFrame.MarginBottom=0
 $q.TextFrame.WordWrap=-1;$q.TextFrame.AutoSize=0
 $q.TextFrame.TextRange.Text=$str;$q.TextFrame.TextRange.Font.Name='Segoe UI'
 $q.TextFrame.TextRange.Font.Size=$size;$q.TextFrame.TextRange.Font.Color.RGB=$color
 $q.TextFrame.TextRange.Font.Bold=[int](-[int]$bold)
 return $q
}
$s.FollowMasterBackground=$false;$s.Background.Fill.Solid();$s.Background.Fill.ForeColor.RGB=$bg
$panel=Box 490 145 710 430 $pale;$panel.ZOrder(1)
$accent=Box 490 145 710 5 $lime;$accent.ZOrder(1)
$logo=$s.Shapes.Item('Picture 8');$logo.Left=48;$logo.Top=38;$logo.Width=34;$logo.Height=34
Txt 'PEREDACHA' 95 43 260 30 20 $ink $true | Out-Null
Txt 'ИНСТРУКЦИЯ ДЛЯ СОТРУДНИКОВ' 750 48 400 25 13 $green $true | Out-Null
Txt 'Руководство' 48 166 445 65 43 $ink $true | Out-Null
Txt 'по работе в' 48 225 430 62 43 $ink $true | Out-Null
Txt 'CRM' 40 280 440 155 120 $green $true | Out-Null
Box 50 461 44 4 $lime | Out-Null
Txt "Основные разделы`rи рабочие операции" 50 488 410 76 23 $muted | Out-Null
$card=Box 526 224 647 314 $white
$card.Shadow.Visible=-1;$card.Shadow.Transparency=0.88;$card.Shadow.Blur=16;$card.Shadow.OffsetX=0;$card.Shadow.OffsetY=8
$img=$s.Shapes.Item('Picture 14');$img.LockAspectRatio=-1;$img.Width=623;$img.Left=538;$img.Top=243;$img.ZOrder(0)
Txt 'РАБОЧАЯ СРЕДА PEREDACHA' 530 181 530 24 13 $green $true | Out-Null
Box 48 616 1104 1 (RGB 215 225 210) | Out-Null
Txt 'CRM ПЕРЕДАЧА | AKVILON-PEREDACHA.RU' 48 636 800 20 10 $muted | Out-Null
Txt '01' 1120 635 40 22 11 $muted | Out-Null
$out=Join-Path $root 'output/pptx/CRM_Peredacha_Visual_Guide_Final4.pptx'
$deck.SaveAs($out)
$deck.SaveAs((Join-Path $root 'output/pdf/CRM_Peredacha_Visual_Guide_Final4.pdf'),32)
$s.Export((Join-Path $root 'output/cover-final4.png'),'PNG',1600,900)
$issues=@()
foreach($q in $s.Shapes){if($q.HasTextFrame -and $q.TextFrame.HasText){if($q.TextFrame.TextRange.BoundHeight -gt $q.Height+2){$issues+=$q.TextFrame.TextRange.Text}}}
Write-Output ('Text overflow issues: '+$issues.Count)
$deck.Close();$app.Quit()
