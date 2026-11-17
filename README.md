# mishabetmen Android

Сборка APK через GitHub Actions.

## Как собрать APK

1. Создай **новый** репозиторий на GitHub (можно приватный).
2. Залей **все файлы из этого архива** в корень репозитория:
   - `main.py`
   - `app_android.py`
   - `security.py`
   - `license_keys.py`
   - `buildozer.spec`
   - папку `.github` (вместе с workflows)

3. После заливки зайди во вкладку **Actions** → выбери workflow **Build Android APK** → **Run workflow**.

4. Когда сборка закончится (обычно 15–25 минут), скачай артефакт `mishabetmen-apk` — внутри будет `.apk` файл.

## Важно
- Файлы должны лежать **в корне** репозитория, а не внутри папки.
- Папку `.github` обязательно нужно залить (в ней workflow).
