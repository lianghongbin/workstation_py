from vika_client import VikaClient

vika = VikaClient("dstsnDVylQhjuBiSEo")


def upload():
    photo = "../web/static/image/demo.webp"
    result = vika.update_record_with_attachment("recBmEpVpQxkd", "异常照片", photo)

if __name__ == "__main__":
    upload()

