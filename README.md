# CacheSade

CacheSade, Windows'ta yalnız açıkça tanımlanmış ve yeniden oluşturulabilir önbellekleri tarayan küçük bir masaüstü uygulamasıdır. Tarama kendiliğinden hiçbir şey silmez. Temizlik için kategori seçimi ve ikinci bir uygulama içi onay gerekir.

## Desteklenen alanlar

- Windows DirectX shader cache (`%LOCALAPPDATA%\D3DSCache`)
- NVIDIA DX/GL shader cache ve NV_Cache
- AMD DX/GL/Vulkan shader cache
- Intel shader cache (`AppData\LocalLow\Intel\ShaderCache`)
- Discord'un resmi olarak belirtilen `Cache` klasörü
- Epic Games Launcher `webcache*` klasörleri
- Kullanıcı TEMP klasöründe yalnız 7 günden eski dosyalar

Tarayıcı profilleri, çerezler, parolalar, İndirilenler, Belgeler, oyun kayıtları, Geri Dönüşüm Kutusu ve bilinmeyen `Cache` klasörleri kapsam dışıdır. Kilitli/erişilemeyen dosyalar atlanır. Shader cache temizliğinden sonra ilk oyun açılışında geçici derleme veya takılma görülebilir.

## Kullanım

En kolay yol: [`release/CacheSade.exe`](release/CacheSade.exe) dosyasını indirip çalıştırın. Yönetici yetkisi gerekmez. İndirilen dosyanın SHA-256 değeri [`release/SHA256SUMS.txt`](release/SHA256SUMS.txt) içinde bulunur.

Kaynak koddan çalıştırmak için Python 3.11+ gerekir:

```powershell
python -m cachesade
```

Testler gerçek kullanıcı önbelleklerine dokunmaz; yalnız geçici test klasörleri kullanır:

```powershell
python -m unittest discover -s tests -v
```

Tek dosyalık EXE üretmek için:

```powershell
.\build.ps1
```

Çıktı: `dist\CacheSade.exe`

## Güvenlik yaklaşımı

- Yalnız sabit, dar bir izin listesi taranır; genel `*Cache*` araması yapılmaz.
- Yeniden ayrıştırma noktaları/sembolik bağlantılar takip edilmez.
- Bilinen kök klasör korunur, yalnız içindeki aday dosyalar silinir.
- Kullanıcı TEMP alanında 7 günlük yaş sınırı vardır.
- Temizlik öncesi kategori, boyut ve yol görünür; son bir onay istenir.

## Kural kaynakları

- [Microsoft: Storage Sense ve geçici dosyalar](https://support.microsoft.com/en-us/windows/experience/storage-filemanagement/manage-drive-space-with-storage-sense)
- [NVIDIA: Shader cache dosyalarını silme](https://nvidia.custhelp.com/app/answers/detail/a_id/5735/)
- [AMD Community: AMD Local AppData shader cache ve Reset Shader Cache](https://community.amd.com/t5/pc-drivers-software/is-there-a-way-to-relocate-the-cache-folders/td-p/554089)
- [Intel Community: Intel ShaderCache konumu](https://community.intel.com/t5/Graphics/Shader-cache-files-showing-device-id-and-extension-saying-0/m-p/1644747)
- [Discord: Windows cache yolu](https://support.discord.com/hc/en-us/articles/31623498041623-Discord-Troubleshooting-Guide)
- [Epic Games: Launcher webcache temizleme](https://www.epicgames.com/help/en-US/c-Category_EpicAccounts/c-TechnicalSupport_GeneralSupport/a000086158)

## Lisans

[MIT](LICENSE)
