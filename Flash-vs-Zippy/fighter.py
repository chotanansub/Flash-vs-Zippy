import pygame

class Fighter():
  def __init__(self, player, x, y, flip, data, sprite_sheet, animation_steps, sounds, is_local=True, font=None):
    self.player = player
    self.size = data[0]
    self.image_scale = data[1]
    self.offset = data[2]
    self.flip = flip  # Initial flip state
    self.animation_list = self.load_images(sprite_sheet, animation_steps)
    self.action = 0  # 0:idle #1:run #2:jump #3:attack1 #4: attack2 #5:hit #6:death
    self.frame_index = 0
    self.image = self.animation_list[self.action][self.frame_index]
    self.update_time = pygame.time.get_ticks()
    self.rect = pygame.Rect((x, y, 80, 180))
    self.vel_y = 0
    self.running = False
    self.jump = False
    self.attacking = False
    self.attack_type = 0
    self.attack_cooldown = 0
    self.attack_sounds = sounds  # Now a list/tuple of sounds for different attacks
    self.hit = False
    self.hit_cooldown = 0  # New: cooldown for hit state to ensure animation plays
    self.health = 100
    self.alive = True
    self.is_local = is_local  # Whether this fighter is controlled locally
    self.remote_input = {}  # Store remote input for network play
    self.font = font  # Store the font for drawing text
    # NEW: Track if this fighter is currently displaying a remote attack animation
    self.remote_attacking = False
    self.remote_attack_action = 0

  def load_images(self, sprite_sheet, animation_steps):
    # extract images from spritesheet
    animation_list = []
    for y, animation in enumerate(animation_steps):
      temp_img_list = []
      for x in range(animation):
        temp_img = sprite_sheet.subsurface(x * self.size, y * self.size, self.size, self.size)
        temp_img_list.append(pygame.transform.scale(temp_img, (self.size * self.image_scale, self.size * self.image_scale)))
      animation_list.append(temp_img_list)
    return animation_list

  def get_state(self):
    """Return the current state of the fighter for network synchronization"""
    return {
      "x": self.rect.x,
      "y": self.rect.y,
      "vel_y": self.vel_y,
      "running": self.running,
      "jump": self.jump,
      "attacking": self.attacking,
      "attack_type": self.attack_type,
      "attack_cooldown": self.attack_cooldown,
      "hit": self.hit,
      "hit_cooldown": self.hit_cooldown,  # Include hit cooldown in state
      "health": self.health,
      "alive": self.alive,
      "action": self.action,
      "frame_index": self.frame_index,
      "flip": self.flip
    }

  def set_state(self, state):
    """Set the state of the fighter from network data"""
    if not state:
        return
    
    # Always prioritize health updates
    remote_health = state.get("health", self.health)
    if remote_health < self.health:
        # Health decreased - definitely apply this change
        old_health = self.health
        self.health = remote_health
        print(f"Health sync: {old_health} -> {remote_health}")
        
        # If health decreased, ensure we show the hit animation
        if not self.hit and self.is_local:  # Only set hit for local fighter
            self.hit = True
            self.hit_cooldown = 45
    
    # Update the rest of the state
    self.rect.x = state.get("x", self.rect.x)
    self.rect.y = state.get("y", self.rect.y)
    self.vel_y = state.get("vel_y", self.vel_y)
    self.running = state.get("running", self.running)
    self.jump = state.get("jump", self.jump)
    
    # CHANGED: Special handling for remote attack animations
    remote_attacking = state.get("attacking", False)
    remote_action = state.get("action", 0)
    
    # If this is a remote fighter and it's attacking, store that state
    if not self.is_local and remote_attacking:
        # This is an attack animation coming from the network
        self.remote_attacking = True
        self.remote_attack_action = remote_action
        self.attacking = True
        self.attack_type = state.get("attack_type", 1)
        
        # Force the animation to attack even if we're in hit animation
        # This is a special case to ensure attacks show properly in multiplayer
        if (remote_action == 3 or remote_action == 4) and self.action != remote_action:
            print(f"Remote attack detected, action: {remote_action}")
            self.action = remote_action
            self.frame_index = state.get("frame_index", 0)
            
    elif not self.is_local:
        # Normal state update for non-local fighters when not attacking
        self.attacking = remote_attacking
        self.attack_type = state.get("attack_type", self.attack_type)
        
        # If remote player was attacking but stopped, clear the remote attack flag
        if not remote_attacking:
            self.remote_attacking = False
            self.remote_attack_action = 0
    else:
        # Normal update for local player
        self.attacking = state.get("attacking", self.attacking)
        self.attack_type = state.get("attack_type", self.attack_type)
    
    self.attack_cooldown = state.get("attack_cooldown", self.attack_cooldown)
    
    # Only update hit state if we're not in hit cooldown from a health change
    if self.hit_cooldown <= 0:
        new_hit = state.get("hit", self.hit)
        if new_hit and not self.hit:
            self.hit = True
            self.hit_cooldown = 45
        elif not new_hit:
            self.hit = False
    
    self.alive = state.get("alive", self.alive)
    
    # MODIFIED: Update animation for remote characters differently
    # For local characters, don't override hit animation
    # For remote characters, allow attack animations to override hit
    if self.is_local:
        # Local fighter - don't override hit animation
        if self.action != 5 or self.frame_index == 0:
            self.action = state.get("action", self.action)
            self.frame_index = state.get("frame_index", self.frame_index)
    else:
        # Remote fighter - update animation with special cases
        if (remote_action == 3 or remote_action == 4) and remote_attacking:
            # For attack animations, always update from network
            self.action = remote_action
            self.frame_index = state.get("frame_index", self.frame_index)
        elif self.action != 5 or self.frame_index == 0:
            # For non-attack animations, update unless in hit animation
            self.action = state.get("action", self.action)
            self.frame_index = state.get("frame_index", self.frame_index)
    
    self.flip = state.get("flip", self.flip)

  def set_remote_input(self, input_data):
    """Set the remote input data for network play"""
    self.remote_input = input_data

  def get_input(self):
    """Get the current input state for network synchronization"""
    key = pygame.key.get_pressed()
    
    # Get relevant keys based on player number
    if self.player == 1:
      return {
        "left": key[pygame.K_a],
        "right": key[pygame.K_d],
        "jump": key[pygame.K_w],
        "attack1": key[pygame.K_r],
        "attack2": key[pygame.K_t]
      }
    else:  # player 2
      return {
        "left": key[pygame.K_LEFT],
        "right": key[pygame.K_RIGHT],
        "jump": key[pygame.K_UP],
        "attack1": key[pygame.K_k],
        "attack2": key[pygame.K_l]
      }

  def move(self, screen_width, screen_height, surface, target, round_over):
    SPEED = 10
    GRAVITY = 2
    dx = 0
    dy = 0
    self.running = False
    self.attack_type = 0

    # Only process input if the fighter is alive and round is not over
    if self.alive and not round_over:
      # Process input either locally or from network
      if self.is_local:
        # Get local key presses
        key = pygame.key.get_pressed()
        
        # Check if not currently attacking
        if not self.attacking:
          # Process movement and attacks based on player number
          if self.player == 1:
            # Movement
            if key[pygame.K_a]:
              dx = -SPEED
              self.running = True
            if key[pygame.K_d]:
              dx = SPEED
              self.running = True
            # Jump
            if key[pygame.K_w] and not self.jump:
              self.vel_y = -30
              self.jump = True
            # Attack
            if not self.attacking:
              if key[pygame.K_r]:
                  self.attack_type = 1
                  self.attack(target)
              elif key[pygame.K_t]:
                  self.attack_type = 2
                  self.attack(target)
                    
          elif self.player == 2:
            # Movement
            if key[pygame.K_LEFT]:
              dx = -SPEED
              self.running = True
            if key[pygame.K_RIGHT]:
              dx = SPEED
              self.running = True
            # Jump
            if key[pygame.K_UP] and not self.jump:
              self.vel_y = -30
              self.jump = True
            # Attack
            if key[pygame.K_k] or key[pygame.K_l]:
              
              # Determine attack type
              if not self.attacking:
                if key[pygame.K_k]:
                    self.attack_type = 1
                    self.attack(target)
                elif key[pygame.K_l]:
                    self.attack_type = 2
                    self.attack(target)
      
      else:
        # Process remote input from network
        if self.remote_input:
          # Only process if not attacking
          if not self.attacking:
            # Movement
            if self.remote_input.get("left", False):
              dx = -SPEED
              self.running = True
            if self.remote_input.get("right", False):
              dx = SPEED
              self.running = True
            # Jump
            if self.remote_input.get("jump", False) and not self.jump:
              self.vel_y = -30
              self.jump = True
            # Attack
            if self.remote_input.get("attack1", False) or self.remote_input.get("attack2", False):
              # Determine attack type
              if self.remote_input.get("attack1", False):
                self.attack_type = 1
              if self.remote_input.get("attack2", False):
                self.attack_type = 2
              self.attack(target)

    # Apply gravity
    self.vel_y += GRAVITY
    dy += self.vel_y

    # Ensure player stays on screen
    if self.rect.left + dx < 0:
      dx = -self.rect.left
    if self.rect.right + dx > screen_width:
      dx = screen_width - self.rect.right
    if self.rect.bottom + dy > screen_height - 110:
      self.vel_y = 0
      self.jump = False
      dy = screen_height - 110 - self.rect.bottom

    # Update player position
    self.rect.x += dx
    self.rect.y += dy

    # Adjust facing direction based on relative positions
    # For player 1 (Zippy), normal flip orientation is True (facing right)
    # For player 2 (Flash), normal flip orientation is False (facing left)
    if self.player == 1:  # Zippy
      if target.rect.centerx < self.rect.centerx:
        # Target is to the left, so Zippy should face left
        self.flip = False  # Flip to face left
      else:
        # Target is to the right, so Zippy should face right
        self.flip = True   # Normal orientation for Zippy
    else:  # Flash (player 2)
      if target.rect.centerx > self.rect.centerx:
        # Target is to the right, so Flash should face right
        self.flip = True   # Flip to face right
      else:
        # Target is to the left, so Flash should face left
        self.flip = False  # Normal orientation for Flash

    # Apply attack cooldown
    if self.attack_cooldown > 0:
      self.attack_cooldown -= 1

  def update(self):
    # MODIFIED: Updated action priorities to handle remote attacks differently
    if self.health <= 0:
      self.health = 0
      self.alive = False
      self.update_action(6)  # 6:death
    elif not self.is_local and self.remote_attacking:
      # For non-local (remote) fighters, prioritize showing attack animations
      # even if being hit, to ensure attacks are visible to the opponent
      if self.attack_type == 1:
        self.update_action(3)  # 3:attack1
      elif self.attack_type == 2:
        self.update_action(4)  # 4:attack2
    elif self.hit == True:
      self.update_action(5)  # 5:hit
    elif self.attacking == True:
      if self.attack_type == 1:
        self.update_action(3)  # 3:attack1
      elif self.attack_type == 2:
        self.update_action(4)  # 4:attack2
    elif self.jump == True:
      self.update_action(2)  # 2:jump
    elif self.running == True:
      self.update_action(1)  # 1:run
    else:
      self.update_action(0)  # 0:idle

    animation_cooldown = 50
    
    # Get the correct animation image
    current_image = self.animation_list[self.action][self.frame_index]
    
    # Scale up attack2 animation by 2x
    if self.action == 4:  # If it's attack2
      # Create a larger image for attack2 animation
      scaled_width = current_image.get_width() * 2
      scaled_height = current_image.get_height() * 2
      current_image = pygame.transform.scale(current_image, (scaled_width, scaled_height))
    
    # Update image
    self.image = current_image
    
    # Check if enough time has passed since the last update
    if pygame.time.get_ticks() - self.update_time > animation_cooldown:
      self.frame_index += 1
      self.update_time = pygame.time.get_ticks()
    # Check if the animation has finished
    if self.frame_index >= len(self.animation_list[self.action]):
      # If the player is dead then end the animation
      if self.alive == False:
        self.frame_index = len(self.animation_list[self.action]) - 1
      else:
        self.frame_index = 0
        # Check if an attack was executed
        if self.action == 3 or self.action == 4:
          self.attacking = False
          self.attack_cooldown = 20
          
          # MODIFIED: Clean up remote attack state when animation finishes
          if not self.is_local:
            self.remote_attacking = False
            self.remote_attack_action = 0
            
        # Check if damage was taken
        if self.action == 5:
          self.hit = False
          # If the player was in the middle of an attack, then the attack is stopped
          # MODIFIED: Only cancel attack animation for local fighters
          # This allows remote fighters to complete their attack animation
          if self.is_local:
            self.attacking = False
            self.attack_cooldown = 20
    
    # Update hit cooldown if active
    if self.hit_cooldown > 0:
      self.hit_cooldown -= 1

  # Update the attack method in Fighter class to separate animation from hit detection

  def attack(self, target):
      hit_successful = False  # Track whether a hit occurred
      
      if self.attack_cooldown == 0:
          # Execute attack
          self.attacking = True
          
          # Play the appropriate sound based on attack type
          if self.attack_type == 1:
              self.attack_sounds[0].play()  # Attack1 sound
          elif self.attack_type == 2:
              self.attack_sounds[1].play()  # Attack2 sound
          
          # Create a hitbox based on attack type - attack2 has double size
          if self.attack_type == 2:
              # Larger hitbox for attack type 2 (twice as large)
              if self.flip:
                  # Facing right
                  attacking_rect = pygame.Rect(self.rect.centerx, 
                                          self.rect.y, 
                                          5.0 * self.rect.width, 
                                          self.rect.height)
              else:
                  # Facing left
                  attacking_rect = pygame.Rect(self.rect.centerx - 5.0 * self.rect.width, 
                                          self.rect.y, 
                                          5.0 * self.rect.width, 
                                          self.rect.height)
          else:
              # Regular hitbox for attack type 1
              if self.flip:
                  # Facing right
                  attacking_rect = pygame.Rect(self.rect.centerx, 
                                          self.rect.y, 
                                          2.5 * self.rect.width, 
                                          self.rect.height)
              else:
                  # Facing left
                  attacking_rect = pygame.Rect(self.rect.centerx - 2.5 * self.rect.width, 
                                          self.rect.y, 
                                          2.5 * self.rect.width, 
                                          self.rect.height)
          
          # Only check for hit collision if this is a local player
          # For remote players, hit detection is done on their end
          if self.is_local and attacking_rect.colliderect(target.rect):
              # Only apply damage if target is not in hit cooldown
              if target.hit_cooldown <= 0:
                  # Apply damage
                  prev_health = target.health
                  target.health -= 10
                  print(f"HIT! Health reduced from {prev_health} to {target.health}")
                  target.hit = True
                  target.hit_cooldown = 45  # Set the hit cooldown
                  hit_successful = True  # Mark that a hit occurred
                  
      return hit_successful  # Return whether a hit was successful

  def update_action(self, new_action):
    # Check if the new action is different to the previous one
    if new_action != self.action:
      self.action = new_action
      # Update the animation settings
      self.frame_index = 0
      self.update_time = pygame.time.get_ticks()

  def draw(self, surface):
    img = pygame.transform.flip(self.image, self.flip, False)
    
    # Adjust offset for attack2 (bigger animation)
    if self.action == 4:  # If it's attack2
      # For attack2, we need to adjust the position since the image is larger
      offset_x = self.offset[0] * self.image_scale
      offset_y = self.offset[1] * self.image_scale
      
      # Move the animation up more by increasing the Y offset
      extra_height_offset = img.get_height() * 0.1  # Lift the animation higher
      
      # If attacking with attack2, adjust position for the larger animation
      if self.flip:  # Facing right
        surface.blit(img, (self.rect.x - offset_x - img.get_width()/4, 
                          self.rect.y - offset_y - img.get_height()/4 - extra_height_offset))
      else:  # Facing left
        surface.blit(img, (self.rect.x - offset_x - img.get_width()/4, 
                          self.rect.y - offset_y - img.get_height()/4 - extra_height_offset))
    else:
      # Normal drawing for other animations
      surface.blit(img, (self.rect.x - (self.offset[0] * self.image_scale), 
                         self.rect.y - (self.offset[1] * self.image_scale)))
                         
  def draw_floating_text(self, surface, game_res):
    """Draw floating player name text above the fighter"""
    player_text = f"Player {self.player}"
    
    # Calculate position above the fighter
    text_x = self.rect.centerx +25  # Center the text above the fighter
    text_y = self.rect.y - 40       # Position it above the fighter
    
    # Use the font passed during initialization, or get it if not available
    font = self.font
    if font is None:
        # For backwards compatibility, load the font from game_res
        _, font, _, _ = game_res.load_fonts()
    
    # Draw white text with a black outline for better visibility
    game_res.draw_text(surface, player_text, font, game_res.BLACK, text_x + 2, text_y + 2)  # Shadow
    game_res.draw_text(surface, player_text, font, game_res.WHITE, text_x, text_y)  # Main text