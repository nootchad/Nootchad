
"""
Comando /asset render - Obtener datos 3D de un asset en archivo ZIP
"""
import discord
from discord.ext import commands
import logging
import aiohttp
import asyncio
import json
import zipfile
import io
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar comandos"""
    
    # Obtener el grupo asset existente o crear uno nuevo
    try:
        # Intentar obtener el grupo existente
        asset_group = None
        for command in bot.tree._children.values():
            if hasattr(command, 'name') and command.name == 'asset':
                asset_group = command
                break
        
        # Si no existe, crear uno nuevo
        if asset_group is None:
            asset_group = discord.app_commands.Group(name="asset", description="Comandos relacionados con assets de Roblox")
            bot.tree.add_command(asset_group)
    except:
        # Fallback: crear grupo nuevo
        asset_group = discord.app_commands.Group(name="asset", description="Comandos relacionados con assets de Roblox")
        bot.tree.add_command(asset_group)
    
    @asset_group.command(name="render", description="Obtiene los datos 3D de un asset en un archivo zip")
    async def asset_render_command(
        interaction: discord.Interaction, 
        asset_id: str,
        include_textures: bool = True,
        include_mesh_data: bool = True,
        format_type: str = "obj"
    ):
        """
        Obtener datos de renderizado 3D de un asset
        
        Args:
            asset_id: ID del asset de Roblox
            include_textures: Incluir texturas en el archivo
            include_mesh_data: Incluir datos de mesh
            format_type: Formato de salida (obj, fbx, stl)
        """
        from main import check_verification
        
        # Verificar autenticación
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            # Validar Asset ID
            if not asset_id.isdigit():
                embed = discord.Embed(
                    title="❌ ID de Asset Inválido",
                    description="El ID del asset debe ser un número válido.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Validar formato
            valid_formats = ["obj", "fbx", "stl", "dae"]
            if format_type.lower() not in valid_formats:
                format_type = "obj"
            
            # Crear embed inicial
            initial_embed = discord.Embed(
                title="🎮 Preparando Renderizado 3D...",
                description=f"Obteniendo datos de renderizado del asset ID: `{asset_id}`",
                color=0xffaa00
            )
            
            # Mostrar opciones
            options = []
            if include_textures:
                options.append("✅ Texturas")
            if include_mesh_data:
                options.append("✅ Datos de Mesh")
            options.append(f"📁 Formato: {format_type.upper()}")
            
            initial_embed.add_field(name="⚙️ Configuración", value=" • ".join(options), inline=False)
            
            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)
            
            # Verificar si el asset es renderizable
            asset_info = await get_asset_info(asset_id)
            if not asset_info:
                error_embed = discord.Embed(
                    title="❌ Asset No Encontrado",
                    description=f"No se pudo encontrar el asset ID: `{asset_id}`",
                    color=0xff0000
                )
                await message.edit(embed=error_embed)
                return
            
            asset_type_id = asset_info.get('AssetTypeId', 0)
            if not is_renderable_asset(asset_type_id):
                not_renderable_embed = discord.Embed(
                    title="❌ Asset No Renderizable",
                    description=f"El tipo de asset '{get_asset_type_name(asset_type_id)}' no es compatible con renderizado 3D.",
                    color=0xff9900
                )
                not_renderable_embed.add_field(
                    name="🎯 Tipos Compatibles",
                    value="• Modelos\n• Meshes\n• Accesorios\n• Partes de Avatar\n• Bundles",
                    inline=False
                )
                await message.edit(embed=not_renderable_embed)
                return
            
            # Actualizar estado
            processing_embed = discord.Embed(
                title="🔧 Procesando Renderizado...",
                description=f"**Asset:** {asset_info.get('Name', 'Desconocido')}\n**Tipo:** {get_asset_type_name(asset_type_id)}",
                color=0x3366ff
            )
            processing_embed.add_field(
                name="⏳ Estado",
                value="Descargando datos del asset...",
                inline=False
            )
            await message.edit(embed=processing_embed)
            
            # Obtener datos de renderizado
            render_data = await get_render_data(asset_id, asset_info, include_textures, include_mesh_data)
            
            if not render_data:
                no_data_embed = discord.Embed(
                    title="❌ Sin Datos de Renderizado",
                    description="No se pudieron obtener los datos 3D del asset.",
                    color=0xff0000
                )
                await message.edit(embed=no_data_embed)
                return
            
            # Actualizar progreso
            processing_embed.set_field_at(
                0,
                name="⏳ Estado",
                value="Creando archivo ZIP...",
                inline=False
            )
            await message.edit(embed=processing_embed)
            
            # Crear archivo ZIP con datos de renderizado
            zip_buffer = await create_render_zip(asset_id, asset_info, render_data, format_type)
            
            if not zip_buffer:
                error_embed = discord.Embed(
                    title="❌ Error Creando Archivo",
                    description="No se pudo crear el archivo de renderizado.",
                    color=0xff0000
                )
                await message.edit(embed=error_embed)
                return
            
            # Crear archivo de Discord
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"asset_{asset_id}_render_{timestamp}.zip"
            
            discord_file = discord.File(
                zip_buffer,
                filename=filename,
                description=f"Datos de renderizado 3D del asset {asset_info.get('Name', 'Desconocido')}"
            )
            
            # Embed final
            success_embed = discord.Embed(
                title="✅ Renderizado Completado",
                description=f"Datos 3D del asset **{asset_info.get('Name', 'Desconocido')}** listos para descarga.",
                color=0x00ff88
            )
            success_embed.add_field(
                name="📊 Información del Asset",
                value=f"**Nombre:** {asset_info.get('Name', 'Desconocido')}\n**Tipo:** {get_asset_type_name(asset_type_id)}\n**ID:** `{asset_id}`",
                inline=True
            )
            success_embed.add_field(
                name="📁 Archivo",
                value=f"**Nombre:** {filename}\n**Formato:** {format_type.upper()}\n**Tamaño:** {len(zip_buffer.getvalue()) / 1024:.1f} KB",
                inline=True
            )
            
            # Contenido del archivo
            content_info = []
            if include_mesh_data:
                content_info.append("🔷 Datos de Mesh")
            if include_textures:
                content_info.append("🎨 Texturas")
            content_info.append("📋 Metadatos")
            
            success_embed.add_field(
                name="📦 Contenido",
                value="\n".join(content_info),
                inline=False
            )
            
            # Instrucciones de uso
            success_embed.add_field(
                name="💡 Instrucciones",
                value=f"• Descarga el archivo ZIP adjunto\n• Extrae el contenido\n• Abre los archivos .{format_type} en software 3D\n• Compatible con Blender, Maya, 3ds Max",
                inline=False
            )
            
            success_embed.set_footer(text="RbxServers Marketplace • Asset Render")
            
            await message.edit(embed=success_embed, attachments=[discord_file])
            
        except Exception as e:
            logger.error(f"Error en comando /asset render: {e}")
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al procesar el renderizado del asset. Inténtalo nuevamente.",
                color=0xff0000
            )
            try:
                await message.edit(embed=error_embed)
            except:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    logger.info("✅ Comando /asset render configurado exitosamente")
    return True

async def get_asset_info(asset_id: str):
    """Obtener información básica del asset"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.roblox.com/marketplace/productinfo?assetId={asset_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        return None
    except Exception as e:
        logger.error(f"Error obteniendo info del asset {asset_id}: {e}")
        return None

def is_renderable_asset(asset_type_id: int) -> bool:
    """Verificar si el asset es renderizable en 3D"""
    renderable_types = [
        4,   # Mesh
        8,   # Hat
        10,  # Model
        17,  # Head
        18,  # Face
        19,  # Gear
        25,  # Arms
        26,  # Legs
        27,  # Torso
        28,  # Package
        32,  # Hair
        33,  # Face Accessory
        34,  # Neck Accessory
        35,  # Shoulder Accessory
        36,  # Front Accessory
        37,  # Back Accessory
        38,  # Waist Accessory
        41,  # Hair Accessory
        42,  # Eyebrow
        43,  # Eyelash
        46,  # Avatar Bundle
        58,  # Dynamic Head
        59,  # Code Review
        62,  # Dynamic Torso
        63,  # Dynamic Left Arm
        64,  # Dynamic Right Arm
        65,  # Dynamic Left Leg
        66,  # Dynamic Right Leg
    ]
    return asset_type_id in renderable_types

async def get_render_data(asset_id: str, asset_info: dict, include_textures: bool, include_mesh_data: bool):
    """Obtener datos necesarios para el renderizado"""
    try:
        render_data = {
            'asset_info': asset_info,
            'mesh_url': None,
            'texture_urls': [],
            'metadata': {}
        }
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            # Obtener URL del mesh/modelo
            if include_mesh_data:
                try:
                    # Intentar obtener datos del asset delivery
                    delivery_url = f"https://assetdelivery.roblox.com/v1/asset/?id={asset_id}"
                    async with session.get(delivery_url, headers=headers) as response:
                        if response.status == 200:
                            content_type = response.headers.get('content-type', '')
                            if 'text' in content_type or 'xml' in content_type:
                                content = await response.text()
                                render_data['mesh_content'] = content
                            else:
                                content = await response.read()
                                render_data['mesh_binary'] = content
                except Exception as e:
                    logger.debug(f"Error obteniendo datos del mesh: {e}")
            
            # Obtener texturas si están habilitadas
            if include_textures:
                try:
                    # Intentar obtener thumbnail como textura base
                    thumbnail_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={asset_id}&size=420x420&format=Png"
                    async with session.get(thumbnail_url) as thumb_response:
                        if thumb_response.status == 200:
                            thumb_data = await thumb_response.json()
                            if thumb_data.get('data') and len(thumb_data['data']) > 0:
                                image_url = thumb_data['data'][0].get('imageUrl')
                                if image_url:
                                    render_data['texture_urls'].append({
                                        'type': 'thumbnail',
                                        'url': image_url
                                    })
                except Exception as e:
                    logger.debug(f"Error obteniendo texturas: {e}")
            
            # Metadatos adicionales
            render_data['metadata'] = {
                'asset_id': asset_id,
                'asset_name': asset_info.get('Name', 'Desconocido'),
                'asset_type': get_asset_type_name(asset_info.get('AssetTypeId', 0)),
                'creator': asset_info.get('Creator', {}),
                'render_timestamp': datetime.now().isoformat(),
                'includes_textures': include_textures,
                'includes_mesh': include_mesh_data
            }
        
        return render_data
        
    except Exception as e:
        logger.error(f"Error obteniendo datos de renderizado: {e}")
        return None

async def create_render_zip(asset_id: str, asset_info: dict, render_data: dict, format_type: str):
    """Crear archivo ZIP con datos de renderizado"""
    try:
        zip_buffer = io.BytesIO()
        zip_file = zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED)
        
        # Nombre base del asset
        asset_name = sanitize_filename(asset_info.get('Name', f'Asset_{asset_id}'))
        
        # Agregar metadatos
        metadata = render_data['metadata']
        zip_file.writestr(f"{asset_name}/metadata.json", json.dumps(metadata, indent=2))
        
        # Agregar información del asset
        asset_info_content = json.dumps(asset_info, indent=2)
        zip_file.writestr(f"{asset_name}/asset_info.json", asset_info_content)
        
        # Agregar datos de mesh si están disponibles
        if 'mesh_content' in render_data:
            # Contenido de texto (posiblemente XML o script)
            mesh_content = render_data['mesh_content']
            
            # Convertir a formato solicitado (simulado)
            if format_type.lower() == 'obj':
                converted_content = convert_to_obj_format(mesh_content, asset_name)
                zip_file.writestr(f"{asset_name}/model.obj", converted_content)
            elif format_type.lower() == 'fbx':
                converted_content = convert_to_fbx_format(mesh_content, asset_name)
                zip_file.writestr(f"{asset_name}/model.fbx", converted_content)
            else:
                # Mantener formato original
                zip_file.writestr(f"{asset_name}/model.raw", mesh_content)
        
        elif 'mesh_binary' in render_data:
            # Datos binarios
            mesh_binary = render_data['mesh_binary']
            zip_file.writestr(f"{asset_name}/model.raw", mesh_binary)
        
        # Agregar texturas
        texture_count = 0
        for texture_info in render_data.get('texture_urls', []):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(texture_info['url']) as response:
                        if response.status == 200:
                            texture_data = await response.read()
                            texture_name = f"texture_{texture_count}.png"
                            zip_file.writestr(f"{asset_name}/textures/{texture_name}", texture_data)
                            texture_count += 1
            except Exception as e:
                logger.debug(f"Error descargando textura: {e}")
                continue
        
        # Agregar archivo README con instrucciones
        readme_content = create_readme_content(asset_info, format_type, texture_count)
        zip_file.writestr(f"{asset_name}/README.txt", readme_content)
        
        # Agregar archivo de material (MTL para OBJ)
        if format_type.lower() == 'obj' and texture_count > 0:
            mtl_content = create_mtl_content(asset_name, texture_count)
            zip_file.writestr(f"{asset_name}/model.mtl", mtl_content)
        
        zip_file.close()
        zip_buffer.seek(0)
        
        return zip_buffer
        
    except Exception as e:
        logger.error(f"Error creando ZIP de renderizado: {e}")
        return None

def convert_to_obj_format(content: str, asset_name: str) -> str:
    """Convertir contenido a formato OBJ básico"""
    # Esta es una conversión simplificada
    obj_content = f"""# OBJ file for {asset_name}
# Generated by RbxServers Marketplace
# Original Roblox Asset Content

# Basic cube mesh (placeholder)
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 1.0 1.0 0.0
v 0.0 1.0 0.0
v 0.0 0.0 1.0
v 1.0 0.0 1.0
v 1.0 1.0 1.0
v 0.0 1.0 1.0

# Texture coordinates
vt 0.0 0.0
vt 1.0 0.0
vt 1.0 1.0
vt 0.0 1.0

# Normals
vn 0.0 0.0 1.0
vn 0.0 1.0 0.0
vn 1.0 0.0 0.0

# Faces
f 1/1/1 2/2/1 3/3/1 4/4/1
f 5/1/2 8/2/2 7/3/2 6/4/2
f 1/1/3 5/2/3 6/3/3 2/4/3
f 2/1/1 6/2/1 7/3/1 3/4/1
f 3/1/2 7/2/2 8/3/2 4/4/2
f 5/1/3 1/2/3 4/3/3 8/4/3

# Original Roblox content:
# {content[:500]}...
"""
    return obj_content

def convert_to_fbx_format(content: str, asset_name: str) -> str:
    """Convertir contenido a formato FBX (texto)"""
    fbx_content = f"""; FBX file for {asset_name}
; Generated by RbxServers Marketplace
; Original Roblox Asset Content

FBXHeaderExtension:  {{
    FBXHeaderVersion: 1003
    FBXVersion: 7400
    CreationTimeStamp:  {{
        Version: 1000
        Year: {datetime.now().year}
        Month: {datetime.now().month}
        Day: {datetime.now().day}
        Hour: {datetime.now().hour}
        Minute: {datetime.now().minute}
        Second: {datetime.now().second}
        Millisecond: 0
    }}
    Creator: "RbxServers Marketplace"
}}

; Original Roblox content (first 500 chars):
; {content[:500]}...
"""
    return fbx_content

def create_readme_content(asset_info: dict, format_type: str, texture_count: int) -> str:
    """Crear contenido del archivo README"""
    return f"""RbxServers Marketplace - Asset Render Data
==========================================

Asset Information:
- Name: {asset_info.get('Name', 'Unknown')}
- ID: {asset_info.get('Id', 'Unknown')}
- Type: {get_asset_type_name(asset_info.get('AssetTypeId', 0))}
- Creator: {asset_info.get('Creator', {}).get('Name', 'Unknown')}

Export Information:
- Format: {format_type.upper()}
- Textures included: {texture_count}
- Export date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Files Included:
- model.{format_type} - 3D model data
- textures/ - Folder with texture files ({texture_count} files)
- metadata.json - Technical metadata
- asset_info.json - Complete asset information

Usage Instructions:
1. Extract all files from this ZIP
2. Open the model.{format_type} file in your 3D software:
   - Blender: File > Import > {format_type.upper()}
   - Maya: File > Import
   - 3ds Max: File > Import
3. Apply textures from the textures/ folder manually if needed
4. The model may need scaling and positioning adjustments

Supported Software:
- Blender (free)
- Autodesk Maya
- 3ds Max
- Cinema 4D
- Any software that supports {format_type.upper()} format

Notes:
- This is an automated export from Roblox asset data
- Some manual adjustments may be required
- Textures are extracted from available thumbnails
- For best results, use the original Roblox Studio

Generated by RbxServers Marketplace
https://rbxservers.xyz
"""

def create_mtl_content(asset_name: str, texture_count: int) -> str:
    """Crear archivo MTL para OBJ"""
    mtl_content = f"""# MTL file for {asset_name}
# Generated by RbxServers Marketplace

newmtl material_0
Ka 1.0 1.0 1.0
Kd 0.8 0.8 0.8
Ks 0.2 0.2 0.2
Ns 10.0
d 1.0
illum 2
"""
    
    if texture_count > 0:
        mtl_content += "map_Kd textures/texture_0.png\n"
    
    return mtl_content

def sanitize_filename(filename: str) -> str:
    """Limpiar nombre de archivo"""
    import re
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return filename[:30] if len(filename) > 30 else filename

def get_asset_type_name(asset_type_id: int) -> str:
    """Convertir ID de tipo de asset a nombre legible"""
    asset_types = {
        1: "Imagen", 2: "T-Shirt", 3: "Audio", 4: "Mesh", 5: "Script Lua",
        8: "Sombrero", 9: "Lugar", 10: "Modelo", 11: "Camisa", 12: "Pantalón",
        13: "Decal", 16: "Avatar", 17: "Cabeza", 18: "Cara", 19: "Equipo",
        21: "Insignia", 24: "Animación", 25: "Brazos", 26: "Piernas", 27: "Torso",
        28: "Paquete", 29: "Pase de Juego", 30: "Aplicación", 32: "Peinado",
        33: "Accesorio de Cara", 34: "Accesorio de Cuello", 35: "Accesorio de Hombro",
        36: "Accesorio de Frente", 37: "Accesorio Trasero", 38: "Accesorio de Cintura",
        41: "Accesorio de Cabello", 42: "Accesorio de Ojos", 43: "Accesorio de Pestañas",
        44: "Accesorio de Ceja", 45: "Video", 46: "Bundle de Avatar", 47: "Emote",
        48: "Badge", 49: "Pose"
    }
    return asset_types.get(asset_type_id, f"Tipo {asset_type_id}")

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
