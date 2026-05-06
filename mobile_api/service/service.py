import base64

class Attachment:

    def create_attachment(self, env, model_name, res_id, file_name, file_data, mimetype):

        allowed_types = ['application/pdf', 'image/jpeg', 'image/png']

        if mimetype not in allowed_types:
            return False, "Only PDF, JPG, PNG files are allowed"

        if not file_data:
            return False, "File data is required"

        try:
            if "," in file_data:
                file_data = file_data.split(",")[1]

            encoded_file = file_data.encode('utf-8')

            attachment = env['ir.attachment'].sudo().create({
                'name': file_name,
                'datas': encoded_file,
                'res_model': model_name,
                'res_id': res_id,
                'mimetype': mimetype,
            })

            return attachment, None

        except Exception as e:
            return False, str(e)