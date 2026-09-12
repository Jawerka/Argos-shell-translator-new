#Requires -Version 5.1
# Обёртка: все аргументы уходят в scripts/dev.ps1 (−Test и т.д.).
& "$PSScriptRoot\scripts\dev.ps1" @args
