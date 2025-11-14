from PIL import Image, ImageDraw

def create_sample_map():
    width, height = 1000, 800
    image = Image.new('RGB', (width, height), color=(200, 230, 255))
    draw = ImageDraw.Draw(image)
    
    draw.rectangle([50, 50, 200, 150], fill=(150, 150, 150), outline=(0, 0, 0), width=2)
    draw.text((60, 100), "Дом 1", fill=(0, 0, 0))
    
    draw.rectangle([300, 100, 450, 200], fill=(150, 150, 150), outline=(0, 0, 0), width=2)
    draw.text((310, 150), "Дом 2", fill=(0, 0, 0))
    
    draw.rectangle([550, 200, 700, 300], fill=(150, 150, 150), outline=(0, 0, 0), width=2)
    draw.text((560, 250), "Дом 3", fill=(0, 0, 0))
    
    draw.rectangle([100, 400, 250, 500], fill=(150, 150, 150), outline=(0, 0, 0), width=2)
    draw.text((110, 450), "Дом 4", fill=(0, 0, 0))
    
    draw.rectangle([400, 450, 550, 550], fill=(150, 150, 150), outline=(0, 0, 0), width=2)
    draw.text((410, 500), "Дом 5", fill=(0, 0, 0))
    
    draw.rectangle([650, 500, 800, 600], fill=(150, 150, 150), outline=(0, 0, 0), width=2)
    draw.text((660, 550), "Дом 6", fill=(0, 0, 0))
    
    image.save('city_map.png')
    print("Создан файл city_map.png с примером карты города")

if __name__ == '__main__':
    create_sample_map()

