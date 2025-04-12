import pygame

class Fighter():
  def __init__(self, player, x, y, flip, data, sprite_sheet, animation_steps, sounds, is_local=True):
    self.player = player
    self.size = data[0]
    self.image_scale = data[1]
    self.offset = data[2]
    self.flip = flip
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
      
    self.rect.x = state.get("x", self.rect.x)
    self.rect.y = state.get("y", self.rect.y)
    self.vel_y = state.get("vel_y", self.vel_y)
    self.running = state.get("running", self.running)
    self.jump = state.get("jump", self.jump)
    self.attacking = state.get("attacking", self.attacking)
    self.attack_type = state.get("attack_type", self.attack_type)
    self.attack_cooldown = state.get("attack_cooldown", self.attack_cooldown)
    
    # Health synchronization - always take the lower health value
    # This ensures hits aren't "missed" in sync
    remote_health = state.get("health", self.health)
    if remote_health < self.health:
      self.health = remote_health
      # If health decreased, ensure we show the hit animation
      if self.hit_cooldown <= 0:
        self.hit = True
        self.hit_cooldown = 45
    
    # Only update hit state if we're not in hit cooldown
    if self.hit_cooldown <= 0:
      new_hit = state.get("hit", self.hit)
      # If this is a new hit, set the cooldown
      if new_hit and not self.hit:
        self.hit = True
        self.hit_cooldown = 45  # Set cooldown (slightly less than animation duration)
      elif not new_hit:
        self.hit = False
    
    # Get hit cooldown from state, but don't override if our local cooldown is higher
    remote_hit_cooldown = state.get("hit_cooldown", 0)
    if remote_hit_cooldown > self.hit_cooldown:
      self.hit_cooldown = remote_hit_cooldown
    
    self.alive = state.get("alive", self.alive)
    
    # Don't override animation states if we're in the middle of a hit animation
    if self.action != 5 or self.frame_index == 0:
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
            if key[pygame.K_r] or key[pygame.K_t]:
              self.attack(target)
              # Determine attack type
              if key[pygame.K_r]:
                self.attack_type = 1
              if key[pygame.K_t]:
                self.attack_type = 2
          
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
              self.attack(target)
              # Determine attack type
              if key[pygame.K_k]:
                self.attack_type = 1
              if key[pygame.K_l]:
                self.attack_type = 2
      
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
              self.attack(target)
              # Determine attack type
              if self.remote_input.get("attack1", False):
                self.attack_type = 1
              if self.remote_input.get("attack2", False):
                self.attack_type = 2

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

    # Ensure players face each other
    if target.rect.centerx > self.rect.centerx:
      # Player 1 looks right when target is to the right
      if self.player == 1:
        self.flip = False
      # Player 2 looks left when target is to the right
      else:
        self.flip = True  
    else:
      # Player 1 looks left when target is to the left
      if self.player == 1:
        self.flip = True
      # Player 2 looks right when target is to the left
      else:
        self.flip = False

    # Apply attack cooldown
    if self.attack_cooldown > 0:
      self.attack_cooldown -= 1

    # Update player position
    self.rect.x += dx
    self.rect.y += dy


  def update(self):
    # Check what action the player is performing
    if self.health <= 0:
      self.health = 0
      self.alive = False
      self.update_action(6)  # 6:death
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
        # Check if damage was taken
        if self.action == 5:
          self.hit = False
          # If the player was in the middle of an attack, then the attack is stopped
          self.attacking = False
          self.attack_cooldown = 20
    
    # Update hit cooldown if active
    if self.hit_cooldown > 0:
      self.hit_cooldown -= 1


  def attack(self, target):
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
        attacking_rect = pygame.Rect(self.rect.centerx - (5.0 * self.rect.width * self.flip), 
                                   self.rect.y, 
                                   5.0 * self.rect.width, 
                                   self.rect.height)
      else:
        # Regular hitbox for attack type 1
        attacking_rect = pygame.Rect(self.rect.centerx - (2.5 * self.rect.width * self.flip), 
                                   self.rect.y, 
                                   2.5 * self.rect.width, 
                                   self.rect.height)
      
      if attacking_rect.colliderect(target.rect):
        # Only apply damage if target is not in hit cooldown
        if target.hit_cooldown <= 0:
          # Apply damage
          prev_health = target.health
          target.health -= 10
          print(f"HIT! Health reduced from {prev_health} to {target.health}")
          target.hit = True
          target.hit_cooldown = 45  # Set the hit cooldown


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
      if self.flip:  # Facing left
        surface.blit(img, (self.rect.x - offset_x - img.get_width()/4, 
                          self.rect.y - offset_y - img.get_height()/4 - extra_height_offset))
      else:  # Facing right
        surface.blit(img, (self.rect.x - offset_x - img.get_width()/4, 
                          self.rect.y - offset_y - img.get_height()/4 - extra_height_offset))
    else:
      # Normal drawing for other animations
      surface.blit(img, (self.rect.x - (self.offset[0] * self.image_scale), 
                         self.rect.y - (self.offset[1] * self.image_scale)))