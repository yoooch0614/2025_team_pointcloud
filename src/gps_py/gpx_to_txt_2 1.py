def convert_gpx_to_txt(input_file, output_file):
    try:
        with open(input_file, "r", encoding='UTF-8') as input_f:
            data = input_f.read()
            # print(data)
        
        with open(output_file, 'w', encoding='UTF-8') as output_f:
            output_f.write(data)
        
        print(f"Data successfully written to {output_file}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    input_file = "project2/0425_road_bike.gpx"
    output_file = "project2/0425_road_bike.txt"
    convert_gpx_to_txt(input_file, output_file)