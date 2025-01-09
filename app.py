import io
from flask import Flask, request, send_from_directory, render_template, send_file
from PIL import Image, ImageOps, ImageFilter,ImageEnhance
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

image_data = {

    "blurred": False,
    "grayscale": False,
    "flip": {
        "horizontal": False,
        "vertical": False
    },
}

undo_stack = []
redo_stack = []

def apply_blur(image):
    return image.filter(ImageFilter.GaussianBlur(5))

def apply_grayscale(image):
    return ImageOps.grayscale(image)

def flip_image(image, horizontal=False, vertical=False):
    if horizontal:
        image = ImageOps.mirror(image)
    if vertical:
        image = ImageOps.flip(image)
    return image

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    if file and allowed_file(file.filename):
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
         # Save current state to undo stack
        undo_stack.append(image_data.copy())
        redo_stack.clear()  # Clear redo stack on new action
        return filename  # Return only the filename
    return 'Invalid file type', 400

@app.route('/image/<filename>')
def get_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/download', methods=['POST'])
def download():
    filename = request.args.get('filename')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    image = Image.open(file_path)

    # Apply edits based on the stored image_data
    if image_data['grayscale']:
        image = image.convert('L')
    if image_data['blurred']:
        image = image.filter(ImageFilter.GaussianBlur(5))
    if image_data['flip']['horizontal']:
        image = ImageOps.mirror(image)
    if image_data['flip']['vertical']:
        image = ImageOps.flip(image)

    # Save the edited image to a BytesIO object
    img_io = io.BytesIO()
    image.save(img_io, 'PNG')
    img_io.seek(0)

    return send_file(img_io, mimetype='image/png', as_attachment=True, attachment_filename='edited-image.png')

@app.route('/edit_image', methods=['POST'])
def edit_image():
    edit_data = request.get_json()
    # Save current state to undo stack
    undo_stack.append(image_data.copy())
    redo_stack.clear()  # Clear redo stack on new action

    # Update image_data with new edits
    image_data.update({
        "blurred": edit_data.get("blurred", image_data["blurred"]),
        "grayscale": edit_data.get("grayscale", image_data["grayscale"]),
        "flip": {
            "horizontal": edit_data.get("flip", {}).get("horizontal", image_data["flip"]["horizontal"]),
            "vertical": edit_data.get("flip", {}).get("vertical", image_data["flip"]["vertical"])
        }
    })

    return jsonify({'message': 'Edit parameters updated successfully'})

@app.route('/undo', methods=['POST'])
def undo():
    if undo_stack:
        redo_stack.append(image_data.copy())
        last_state = undo_stack.pop()
        image_data.update(last_state)
        return jsonify(image_data)
    return "Nothing to undo", 400

@app.route('/redo', methods=['POST'])
def redo():
    if redo_stack:
        undo_stack.append(image_data.copy())
        last_state = redo_stack.pop()
        image_data.update(last_state)
        return jsonify(image_data)
    return "Nothing to redo", 400

@app.route('/grayscale/<filename>')
def grayscale_image(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with Image.open(file_path) as img:
        grayscale_img = apply_grayscale(img)
        grayscale_path = os.path.join(app.config['UPLOAD_FOLDER'], 'grayscale_' + filename)
        grayscale_img.save(grayscale_path)
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'grayscale_' + filename)

@app.route('/blur/<filename>')
def blur_image(filename):
     # Save current state to undo stack
    undo_stack.append(image_data.copy())
    redo_stack.clear()  # Clear redo stack on new action

    # Set blur state to true
    image_data["blurred"] = True

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with Image.open(file_path) as img:
        blurred_img = apply_blur(img)
        blurred_path = os.path.join(app.config['UPLOAD_FOLDER'], 'blurred_' + filename)
        blurred_img.save(blurred_path)
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'blurred_' + filename)
@app.route('/flip_horizontal/<filename>', methods=['GET'])
def flip_horizontal(filename):
     # Check if the image has already been flipped horizontally
    if image_data.get("flip", {}).get("horizontal", False):
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'flip_horizontal_' + filename)

    # Save current state to undo stack
    undo_stack.append(image_data.copy())
    redo_stack.clear()  # Clear redo stack on new action

    # Set flip horizontal state to true
    image_data.setdefault("flip", {})["horizontal"] = True

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with Image.open(file_path) as img:
        flipped_img = flip_image(img, horizontal=True)
        flipped_path = os.path.join(app.config['UPLOAD_FOLDER'], 'flip_horizontal_' + filename)
        flipped_img.save(flipped_path)
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'flip_horizontal_' + filename)

@app.route('/flip_vertical/<filename>', methods=['GET'])
def flip_vertical(filename):
    # Save current state to undo stack
    undo_stack.append(image_data.copy())
    redo_stack.clear()  # Clear redo stack on new action

    # Set flip vertical state to true
    image_data["flip"]["vertical"] = True

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with Image.open(file_path) as img:
        flipped_img = flip_image(img, vertical=True)
        flipped_path = os.path.join(app.config['UPLOAD_FOLDER'], 'flip_vertical_' + filename)
        flipped_img.save(flipped_path)
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'flip_vertical_' + filename)
@app.route('/crop/<filename>', methods=['POST'])
def crop_image(filename):
    data = request.get_json()
    left = data.get('left')
    upper = data.get('upper')
    right = data.get('right')
    lower = data.get('lower')
    
    # Log the received coordinates
    app.logger.debug(f"Received coordinates: left={left}, upper={upper}, right={right}, lower={lower}")
    
    if None in [left, upper, right, lower]:
        return "Invalid coordinates", 400
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with Image.open(file_path) as img:
        # Log the image size
        app.logger.debug(f"Image size: {img.size}")
        
        # Ensure coordinates are within image bounds
        width, height = img.size
        if not (0 <= left < right <= width and 0 <= upper < lower <= height):
            return "Coordinates out of bounds", 400
        
        cropped_img = img.crop((left, upper, right, lower))
        cropped_path = os.path.join(app.config['UPLOAD_FOLDER'], 'cropped_' + filename)
        cropped_img.save(cropped_path)
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'cropped_' + filename)
    


@app.route('/rotate/<filename>/<int:angle>', methods=['GET'])
def rotate_image(filename, angle):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with Image.open(file_path) as img:
        rotated_img = img.rotate(angle, expand=True)
        rotated_path = os.path.join(app.config['UPLOAD_FOLDER'], 'rotate_' + filename)
        rotated_img.save(rotated_path)
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'rotate_' + filename)
@app.route('/brightness/<filename>/<int:brightness>')
def adjust_brightness(filename, brightness):
     # Save current state to undo stack
    undo_stack.append(image_data.copy())
    redo_stack.clear()  # Clear redo stack on new action

    # Set saturation state to the specified level
    image_data["saturation"] = saturation
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with Image.open(file_path) as img:
        enhancer = ImageEnhance.Brightness(img)
        enhanced_img = enhancer.enhance(brightness / 100.0)
        enhanced_path = os.path.join(app.config['UPLOAD_FOLDER'], 'brightness_' + filename)
        enhanced_img.save(enhanced_path)
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'brightness_' + filename)
    
@app.route('/contrast/<filename>/<int:contrast>')
def adjust_contrast(filename, contrast):
    # Save current state to undo stack
    undo_stack.append(image_data.copy())
    redo_stack.clear()  # Clear redo stack on new action

    # Set contrast state to the specified level
    image_data["contrast"] = contrast
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    print(f"Adjusting contrast for {filename} with contrast level {contrast}")
    with Image.open(file_path) as img:
        enhancer = ImageEnhance.Contrast(img)
        enhanced_img = enhancer.enhance(contrast / 100.0)
        enhanced_path = os.path.join(app.config['UPLOAD_FOLDER'], 'contrast_' + filename)
        enhanced_img.save(enhanced_path)
        print(f"Saved enhanced image to {enhanced_path}")
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'contrast_' + filename)
@app.route('/saturation/<filename>/<int:saturation>', methods=['GET'])
def adjust_saturation(filename, saturation):
    # Save current state to undo stack
    undo_stack.append(image_data.copy())
    redo_stack.clear()  # Clear redo stack on new action

    # Set contrast state to the specified level
    image_data["saturation"] = saturation
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with Image.open(file_path) as img:
        enhancer = ImageEnhance.Color(img)
        enhanced_img = enhancer.enhance(saturation / 100.0)
        enhanced_path = os.path.join(app.config['UPLOAD_FOLDER'], 'saturation_' + filename)
        enhanced_img.save(enhanced_path)
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'saturation_' + filename)
@app.route('/exposure/<filename>/<int:exposure>', methods=['GET'])
def adjust_exposure(filename, exposure):
    # Save current state to undo stack
    undo_stack.append(image_data.copy())
    redo_stack.clear()  # Clear redo stack on new action

    # Set contrast state to the specified level
    image_data["exposure"] = exposure
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with Image.open(file_path) as img:
        enhancer = ImageEnhance.Brightness(img)
        enhanced_img = enhancer.enhance(exposure / 100.0)
        enhanced_path = os.path.join(app.config['UPLOAD_FOLDER'], 'exposure_' + filename)
        enhanced_img.save(enhanced_path)
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'exposure_' + filename)       
@app.route('/sharpness/<filename>/<int:sharpness>', methods=['GET'])
def adjust_sharpness(filename, sharpness):
    # Save current state to undo stack
    undo_stack.append(image_data.copy())
    redo_stack.clear()  # Clear redo stack on new action

    # Set contrast state to the specified level
    image_data["sharpness"] = sharpness
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with Image.open(file_path) as img:
        enhancer = ImageEnhance.Sharpness(img)
        enhanced_img = enhancer.enhance(sharpness / 100.0)
        enhanced_path = os.path.join(app.config['UPLOAD_FOLDER'], 'sharpness_' + filename)
        enhanced_img.save(enhanced_path)
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'sharpness_' + filename)        
if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)